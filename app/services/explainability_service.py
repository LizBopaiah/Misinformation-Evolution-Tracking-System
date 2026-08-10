import os
import re
import json
import time
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.fact_check import FactCheckResult
from app.models.sentiment import SentimentResult
from app.models.evolution import EvolutionResult
from app.models.credibility import SourceCredibility
from app.models.report import ResearchReport, ComparisonResult
from app.models.explainability import ExplainabilityResult
from app.services.credibility_service import CredibilityService

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class ExplainabilityService:
    """Service to generate and fetch Explainable AI (XAI) and Model Governance snapshots"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                current_app.logger.error(f"Failed to configure Gemini in ExplainabilityService: {str(e)}")

    def map_confidence_level(self, score):
        """Maps a 0-100 score to confidence level boundaries"""
        if score <= 20.0:
            return "Very Low"
        elif score <= 40.0:
            return "Low"
        elif score <= 60.0:
            return "Medium"
        elif score <= 80.0:
            return "High"
        else:
            return "Very High"

    def generate_fact_explanation(self, search, articles):
        """Generates explainability metrics for the Fact Audit pipeline"""
        verdict = search.fact_check_result or "UNAUDITED"
        is_misinfo = verdict == "MISINFORMATION DETECTED"
        
        # Calculate mock confidence score
        confidence = 85.0 if is_misinfo else 90.0
        confidence_level = self.map_confidence_level(confidence)

        # 1. Evidence Lists (For/Against)
        evidence_for = []
        evidence_against = []
        cred_svc = CredibilityService()

        for art in articles:
            # Check credibility
            normalized_domain = cred_svc.normalize_domain(art.url)
            cred = SourceCredibility.query.filter_by(domain=normalized_domain).first()
            grade = cred.letter_grade if cred else "C"
            score = cred.credibility_score if cred else 70.0

            evidence_obj = {
                "article_id": art.id,
                "article_title": art.title,
                "source_domain": art.source or "Unknown",
                "evidence_snippet": art.content[:200] if art.content else "",
                "evidence_type": "scraped_article",
                "credibility_grade": grade,
                "similarity_score": 100.0
            }

            if is_misinfo:
                # In misinfo searches, low credibility or sensational sites are evidence for misinfo, high are against
                if grade in ('D', 'F', 'C'):
                    evidence_for.append(evidence_obj)
                else:
                    evidence_against.append(evidence_obj)
            else:
                if grade in ('A+', 'A', 'B'):
                    evidence_for.append(evidence_obj)
                else:
                    evidence_against.append(evidence_obj)

        # Limit sizes
        evidence_for = evidence_for[:5]
        evidence_against = evidence_against[:5]

        # 2. Feature Importance
        feature_importance = [
            {
                "feature": "Source Credibility Grade",
                "importance": 0.88,
                "direction": "supports_prediction" if not is_misinfo else "contradicts_prediction",
                "description": f"Reputable domain signals increase confidence in factual veracity."
            },
            {
                "feature": "Contradiction Index",
                "importance": 0.75,
                "direction": "supports_prediction" if is_misinfo else "contradicts_prediction",
                "description": "Variations in claims across domains impact the final classification."
            }
        ]

        # Detailed local explanation narrative
        local_reasoning = {
            "Executive Summary": f"The model evaluated the query '{search.query}' and classified the content as '{verdict}'. This was computed via the MET Hybrid Verification Engine.",
            "Supporting Evidence": f"Found {len(evidence_for)} articles matching characteristics of the prediction, with source domains like " + ", ".join([e["source_domain"] for e in evidence_for]) + ".",
            "Contradicting Evidence": f"Identified {len(evidence_against)} articles containing counter-narratives or reputable credentials.",
            "Confidence Explanation": f"Model confidence is rated at {confidence}% ({confidence_level}) due to source consistency and corroborating fact ratings.",
            "Model Limitations": "Supervised classifiers may misclassify emerging context due to the lack of training data on novel themes.",
            "Feature Importance": "Source reputation and text semantic weights are the primary classification drivers.",
            "Overall Recommendation": "Verify claims with primary medical or scientific journals before reference publication."
        }

        # Try Gemini
        fallback_used = True
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Explain why a fact-checking model classified the query '{search.query}' as '{verdict}'. "
                    f"Write a JSON response with keys: 'Executive Summary', 'Supporting Evidence', "
                    f"'Contradicting Evidence', 'Confidence Explanation', 'Model Limitations', "
                    f"'Feature Importance', 'Overall Recommendation'. Keep responses concise."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    # Clean json tags if present
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if all(k in parsed for k in local_reasoning.keys()):
                        local_reasoning = parsed
                        fallback_used = False
            except Exception as e:
                current_app.logger.warning(f"Fact XAI Gemini call failed: {str(e)}. Using fallback.")

        return {
            "confidence": confidence,
            "confidence_level": confidence_level,
            "evidence_for": evidence_for,
            "evidence_against": evidence_against,
            "feature_importance": feature_importance,
            "explanation": local_reasoning,
            "fallback_used": fallback_used
        }

    def generate_sentiment_explanation(self, search_id):
        """Generates explainability metrics for the Sentiment engine"""
        sentiment = SentimentResult.query.filter_by(search_id=search_id).first()
        dominant_emotion = sentiment.dominant_emotion if sentiment else "Neutral"
        risk_level = sentiment.risk_level if sentiment else "LOW"
        confidence = sentiment.confidence if sentiment else 70.0
        confidence_level = self.map_confidence_level(confidence)

        feature_importance = [
            {
                "feature": "Emotional Strength Indicator",
                "importance": 0.85,
                "direction": "supports_prediction",
                "description": f"High probability of emotion '{dominant_emotion}' flags semantic manipulation risks."
            }
        ]

        local_reasoning = {
            "Executive Summary": f"The semantic tone classifier evaluated the dominant emotion as '{dominant_emotion}' with a '{risk_level}' manipulation risk.",
            "Supporting Evidence": f"Averaged emotion weights showing strong indicators of '{dominant_emotion}'.",
            "Contradicting Evidence": "Minority classes (Joy/Surprise) show lower correlation with manipulation threats.",
            "Confidence Explanation": f"Emotion classifier reports a {confidence}% probability ({confidence_level}) on the dominant class.",
            "Model Limitations": "Short texts can exhibit multi-class emotional features which might confuse classifiers.",
            "Feature Importance": "Probability peaks in negative emotional quadrants dictate risk grading.",
            "Overall Recommendation": "Monitor sentiment shifts as narrative mutations propagate."
        }

        # Try Gemini
        fallback_used = True
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Explain why a sentiment analyzer classified a text collection's dominant emotion as '{dominant_emotion}' "
                    f"with risk level '{risk_level}'. Write a JSON response with keys: 'Executive Summary', 'Supporting Evidence', "
                    f"'Contradicting Evidence', 'Confidence Explanation', 'Model Limitations', 'Feature Importance', "
                    f"'Overall Recommendation'. Keep responses concise."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if all(k in parsed for k in local_reasoning.keys()):
                        local_reasoning = parsed
                        fallback_used = False
            except Exception as e:
                current_app.logger.warning(f"Sentiment XAI Gemini call failed: {str(e)}. Using fallback.")

        return {
            "confidence": confidence,
            "confidence_level": confidence_level,
            "evidence_for": [],
            "evidence_against": [],
            "feature_importance": feature_importance,
            "explanation": local_reasoning,
            "fallback_used": fallback_used
        }

    def generate_evolution_explanation(self, search_id):
        """Generates explainability metrics for the Narrative Evolution engine"""
        evo = EvolutionResult.query.filter_by(search_id=search_id).first()
        drift_score = evo.narrative_drift_score if evo else 0.0
        variants_count = evo.total_variants_detected if evo else 0
        dominant = evo.dominant_narrative if evo else "Unknown"

        confidence = 80.0 if variants_count > 0 else 50.0
        confidence_level = self.map_confidence_level(confidence)

        feature_importance = [
            {
                "feature": "Narrative Drift Index",
                "importance": 0.90,
                "direction": "supports_prediction",
                "description": f"Narrative drift of {drift_score:.1f}% indicates structural variant mutations over time."
            }
        ]

        local_reasoning = {
            "Executive Summary": f"Narrative evolution tracked {variants_count} mutations. The dominant narrative was identified as '{dominant}' with a drift index of {drift_score:.1f}%.",
            "Supporting Evidence": f"Identified distinct variants clustering and semantic similarities changing chronologically.",
            "Contradicting Evidence": "Stable semantic themes that did not drift suggest narrative preservation.",
            "Confidence Explanation": f"Evolution classifier confidence is {confidence}% ({confidence_level}) based on cluster isolation indices.",
            "Model Limitations": "Rapid changes in search timelines can result in sparse clusters.",
            "Feature Importance": "Chronological publish dates and TF-IDF differences are the main drift weights.",
            "Overall Recommendation": "Observe chronological clusters to intercept viral disinformation campaigns."
        }

        # Try Gemini
        fallback_used = True
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Explain why an evolution analyzer reported a narrative drift score of {drift_score}% across {variants_count} variants. "
                    f"Write a JSON response with keys: 'Executive Summary', 'Supporting Evidence', 'Contradicting Evidence', "
                    f"'Confidence Explanation', 'Model Limitations', 'Feature Importance', 'Overall Recommendation'. Keep responses concise."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if all(k in parsed for k in local_reasoning.keys()):
                        local_reasoning = parsed
                        fallback_used = False
            except Exception as e:
                current_app.logger.warning(f"Evolution XAI Gemini call failed: {str(e)}. Using fallback.")

        return {
            "confidence": confidence,
            "confidence_level": confidence_level,
            "evidence_for": [],
            "evidence_against": [],
            "feature_importance": feature_importance,
            "explanation": local_reasoning,
            "fallback_used": fallback_used
        }

    def generate_credibility_explanation(self, search_id):
        """Generates explainability metrics for the Source Credibility engine"""
        articles = Article.query.filter_by(search_id=search_id).all()
        cred_svc = CredibilityService()
        
        scores = []
        for a in articles:
            normalized_domain = cred_svc.normalize_domain(a.url)
            cred = SourceCredibility.query.filter_by(domain=normalized_domain).first()
            if cred:
                scores.append(cred.credibility_score)
            else:
                scores.append(70.0)
                
        avg_score = sum(scores) / len(scores) if scores else 70.0
        avg_grade = cred_svc.get_letter_grade(avg_score)
        confidence_level = self.map_confidence_level(avg_score)

        feature_importance = [
            {
                "feature": "Domain Suffix Weights",
                "importance": 0.80,
                "direction": "supports_prediction",
                "description": "Academic and governmental top-level suffixes (.gov/.edu) significantly increase credibility scores."
            }
        ]

        local_reasoning = {
            "Executive Summary": f"The credibility audit analyzed sources, returning an average trust score of {avg_score:.1f}% ({avg_grade}).",
            "Supporting Evidence": f"Evaluated domains. Found {len(articles)} domains. The most reputable domains lift overall ratings.",
            "Contradicting Evidence": "Low trust domains or HTTP protocols decrease the final trust average.",
            "Confidence Explanation": f"Source trust rating is calculated at {avg_score:.1f}% ({confidence_level}) using multi-factor weights.",
            "Model Limitations": "Reputation lists require periodic updates to catch new domains.",
            "Feature Importance": "Prior third-party fact audit records and TLD suffixes are the main rating parameters.",
            "Overall Recommendation": "Cross-reference unverified news blogs against wire services AP or Reuters."
        }

        # Try Gemini
        fallback_used = True
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Explain why a source credibility engine calculated an average trust rating of {avg_score}% ({avg_grade}). "
                    f"Write a JSON response with keys: 'Executive Summary', 'Supporting Evidence', 'Contradicting Evidence', "
                    f"'Confidence Explanation', 'Model Limitations', 'Feature Importance', 'Overall Recommendation'. Keep responses concise."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if all(k in parsed for k in local_reasoning.keys()):
                        local_reasoning = parsed
                        fallback_used = False
            except Exception as e:
                current_app.logger.warning(f"Credibility XAI Gemini call failed: {str(e)}. Using fallback.")

        return {
            "confidence": avg_score,
            "confidence_level": confidence_level,
            "evidence_for": [],
            "evidence_against": [],
            "feature_importance": feature_importance,
            "explanation": local_reasoning,
            "fallback_used": fallback_used
        }

    def generate_search_explainability(self, search_id, force_refresh=False):
        """Unified function combining all explainability sub-modules"""
        start_time = time.time()
        
        search = db.session.get(SearchHistory, search_id)
        if not search:
            raise ValueError(f"Search history query ID {search_id} not found.")

        # Cache check
        if not force_refresh:
            cached = ExplainabilityResult.query.filter_by(search_id=search_id, explanation_type='search').first()
            if cached:
                current_app.logger.info(f"Cache hit: ExplainabilityResult for search_id {search_id}")
                res_dict = cached.to_dict()
                res_dict["cached"] = True
                return res_dict

        articles = Article.query.filter_by(search_id=search_id).all()

        # Run explainers
        fact = self.generate_fact_explanation(search, articles)
        sentiment = self.generate_sentiment_explanation(search_id)
        evo = self.generate_evolution_explanation(search_id)
        cred = self.generate_credibility_explanation(search_id)

        # Merge results
        prediction = search.fact_check_result or "UNAUDITED"
        
        # Combined average confidence
        conf_scores = [fact["confidence"], sentiment["confidence"], evo["confidence"], cred["confidence"]]
        avg_confidence = round(sum(conf_scores) / len(conf_scores), 2)
        confidence_level = self.map_confidence_level(avg_confidence)

        evidence_for = fact["evidence_for"]
        evidence_against = fact["evidence_against"]

        # Merge feature importance lists
        feature_importance = fact["feature_importance"] + sentiment["feature_importance"] + evo["feature_importance"] + cred["feature_importance"]
        
        # Merge narrative explanations
        unified_explanation = {
            "Executive Summary": fact["explanation"].get("Executive Summary") or sentiment["explanation"].get("Executive Summary") or "No explanation compiled.",
            "Supporting Evidence": fact["explanation"].get("Supporting Evidence") or "No supporting evidence listed.",
            "Contradicting Evidence": fact["explanation"].get("Contradicting Evidence") or "No contradicting evidence listed.",
            "Confidence Explanation": f"Combined prediction confidence is {avg_confidence}% ({confidence_level}). " + fact["explanation"].get("Confidence Explanation", ""),
            "Model Limitations": fact["explanation"].get("Model Limitations") or "General constraints apply.",
            "Feature Importance": fact["explanation"].get("Feature Importance") or "Feature weights analyzed.",
            "Overall Recommendation": fact["explanation"].get("Overall Recommendation") or "Audit findings manually.",
            "fact_details": fact["explanation"],
            "sentiment_details": sentiment["explanation"],
            "evolution_details": evo["explanation"],
            "credibility_details": cred["explanation"]
        }

        fallback_used = any([fact["fallback_used"], sentiment["fallback_used"], evo["fallback_used"], cred["fallback_used"]])
        processing_time = int((time.time() - start_time) * 1000.0)

        # Build Governance Metadata
        model_name = "MET Hybrid Verification & Risk Classifier"
        model_version = "xai_v1.0"
        vectorizer_version = "tfidf_v1.0"
        pipeline_version = "met_pipeline_v1.0"
        inference_method = "fallback" if fallback_used else "model"

        # Check existing to overwrite if forced
        result_record = ExplainabilityResult.query.filter_by(search_id=search_id, explanation_type='search').first()
        if not result_record:
            result_record = ExplainabilityResult(
                user_id=search.user_id,
                search_id=search_id,
                explanation_type='search'
            )
            db.session.add(result_record)

        result_record.prediction = prediction
        result_record.confidence = avg_confidence
        result_record.confidence_level = confidence_level
        result_record.explanation = unified_explanation
        result_record.evidence_for = evidence_for
        result_record.evidence_against = evidence_against
        result_record.feature_importance = feature_importance
        result_record.model_name = model_name
        result_record.model_version = model_version
        result_record.vectorizer_version = vectorizer_version
        result_record.pipeline_version = pipeline_version
        result_record.inference_method = inference_method
        result_record.fallback_used = fallback_used
        result_record.processing_time_ms = processing_time

        db.session.commit()

        res_dict = result_record.to_dict()
        res_dict["cached"] = False
        return res_dict

    def generate_comparison_explanation(self, report_id):
        """Generates explainability metrics for a Comparative Analytics Report"""
        report = db.session.get(ResearchReport, report_id)
        if not report:
            raise ValueError(f"Research report ID {report_id} not found.")

        comp = ComparisonResult.query.filter_by(report_id=report_id).first()
        similarity = comp.similarity_score if comp else 50.0
        confidence_level = self.map_confidence_level(similarity)

        feature_importance = [
            {
                "feature": "Shared Semantic Themes",
                "importance": 0.85,
                "direction": "supports_prediction",
                "description": f"Overlapping themes/keywords increase similarity indices."
            }
        ]

        local_reasoning = {
            "Executive Summary": f"The comparative analytics report '{report.report_name}' was generated. The similarity index was computed as {similarity:.1f}% ({confidence_level}).",
            "Supporting Evidence": f"Analyzed shared keywords and emotion probabilities overlapping between topics.",
            "Contradicting Evidence": "Diverging narrative details and differing publish timelines decrease similarity.",
            "Confidence Explanation": f"Comparison logic similarity score is {similarity:.1f}% ({confidence_level}) based on tf-idf overlap.",
            "Model Limitations": "Report comparisons are limited by the database size of scraped articles.",
            "Feature Importance": "Emotion overlap and shared themes are key inputs.",
            "Overall Recommendation": "Observe shared themes to see how misinformation spreads across topics."
        }

        # Try Gemini
        fallback_used = True
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Explain why a comparative search similarity report has a similarity score of {similarity}%. "
                    f"Write a JSON response with keys: 'Executive Summary', 'Supporting Evidence', 'Contradicting Evidence', "
                    f"'Confidence Explanation', 'Model Limitations', 'Feature Importance', 'Overall Recommendation'. Keep responses concise."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if all(k in parsed for k in local_reasoning.keys()):
                        local_reasoning = parsed
                        fallback_used = False
            except Exception as e:
                current_app.logger.warning(f"Comparison XAI Gemini call failed: {str(e)}. Using fallback.")

        return {
            "confidence": similarity,
            "confidence_level": confidence_level,
            "evidence_for": [],
            "evidence_against": [],
            "feature_importance": feature_importance,
            "explanation": local_reasoning,
            "fallback_used": fallback_used
        }

    def generate_report_explainability(self, report_id, force_refresh=False):
        """Unified comparative report explanation function"""
        start_time = time.time()
        
        report = db.session.get(ResearchReport, report_id)
        if not report:
            raise ValueError(f"Research report ID {report_id} not found.")

        # Cache check
        if not force_refresh:
            cached = ExplainabilityResult.query.filter_by(search_id=None, article_id=report_id, explanation_type='report').first()
            if cached:
                current_app.logger.info(f"Cache hit: ExplainabilityResult for report_id {report_id}")
                res_dict = cached.to_dict()
                res_dict["cached"] = True
                return res_dict

        # Generate details
        comp = self.generate_comparison_explanation(report_id)

        fallback_used = comp["fallback_used"]
        processing_time = int((time.time() - start_time) * 1000.0)

        # Build Governance Metadata
        model_name = "MET Cross-Search Comparer"
        model_version = "comparison_v1.0"
        vectorizer_version = "tfidf_v1.0"
        pipeline_version = "met_pipeline_v1.0"
        inference_method = "fallback" if fallback_used else "model"

        # Check existing to overwrite if forced
        result_record = ExplainabilityResult.query.filter_by(search_id=None, article_id=report_id, explanation_type='report').first()
        if not result_record:
            result_record = ExplainabilityResult(
                user_id=report.user_id,
                article_id=report_id, # Using article_id to store report_id to keep column schema clean
                explanation_type='report'
            )
            db.session.add(result_record)

        result_record.prediction = f"Similarity: {comp['confidence']:.1f}%"
        result_record.confidence = comp["confidence"]
        result_record.confidence_level = comp["confidence_level"]
        result_record.explanation = comp["explanation"]
        result_record.evidence_for = []
        result_record.evidence_against = []
        result_record.feature_importance = comp["feature_importance"]
        result_record.model_name = model_name
        result_record.model_version = model_version
        result_record.vectorizer_version = vectorizer_version
        result_record.pipeline_version = pipeline_version
        result_record.inference_method = inference_method
        result_record.fallback_used = fallback_used
        result_record.processing_time_ms = processing_time

        db.session.commit()

        res_dict = result_record.to_dict()
        res_dict["cached"] = False
        return res_dict
