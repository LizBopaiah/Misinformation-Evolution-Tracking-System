import os
import json
import hashlib
import numpy as np
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.sentiment import SentimentResult
from app.models.evolution import EvolutionResult
from app.models.report import ResearchReport, ComparisonResult
from datetime import datetime
from app.services.nlp_service import preprocess_texts_batch

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class ResearchIntelligenceService:
    """Service to compare search topics, extract shared themes/emotions/claims, and write intelligence reports"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                current_app.logger.error(f"Failed to configure Gemini in ResearchIntelligenceService: {str(e)}")

    def generate_research_profile(self, search_ids):
        """Compiles metadata profiles for all compared search query runs"""
        profiles = []
        for sid in search_ids:
            search = db.session.get(SearchHistory, sid)
            if not search:
                continue

            articles = db.session.query(Article).filter_by(search_id=sid).all()
            article_list = [
                {
                    "id": a.id,
                    "title": a.title,
                    "source": a.source or "Unknown",
                    "published_at": a.published_at.isoformat() if a.published_at else None
                }
                for a in articles
            ]

            profiles.append({
                "search_id": search.id,
                "query": search.query,
                "fact_check_verdict": search.fact_check_result or "UNAUDITED",
                "overall_emotion": search.overall_emotion or "Neutral",
                "overall_risk_level": search.overall_risk_level or "LOW",
                "emotion_distribution": search.aggregated_emotion_distribution,
                "articles_count": len(articles),
                "articles": article_list,
                "created_at": search.created_at.isoformat() if search.created_at else None
            })
        return profiles

    def identify_shared_themes(self, search_ids):
        """Identifies overlapping themes (keywords) between compared searches"""
        search_keywords = {}
        all_features = []

        for sid in search_ids:
            articles = db.session.query(Article).filter_by(search_id=sid).all()
            if not articles:
                continue

            raw_texts = [a.content for a in articles]
            preprocessed = preprocess_texts_batch(raw_texts)
            valid_preprocessed = [txt for txt in preprocessed if txt.strip()]

            if not valid_preprocessed:
                continue

            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(valid_preprocessed)
            feature_names = vectorizer.get_feature_names_out()
            sums = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
            top_indices = sums.argsort()[::-1][:15]
            
            search_keywords[sid] = {feature_names[idx]: float(sums[idx]) for idx in top_indices}
            all_features.extend(list(search_keywords[sid].keys()))

        if not search_keywords:
            return []

        # Count frequencies of keywords across different searches
        shared_counts = {}
        for feat in all_features:
            shared_counts[feat] = shared_counts.get(feat, 0) + 1

        # We keep themes present in at least 2 searches, sorted by frequency, then average TF-IDF
        shared_themes = []
        for word, count in shared_counts.items():
            if count >= 2:
                # Calculate average weight
                weights = [search_keywords[sid][word] for sid in search_keywords if word in search_keywords[sid]]
                avg_weight = float(np.mean(weights))
                shared_themes.append({
                    "keyword": word,
                    "frequency": count,
                    "avg_weight": avg_weight
                })

        shared_themes = sorted(shared_themes, key=lambda x: (x["frequency"], x["avg_weight"]), reverse=True)[:10]
        return [item["keyword"] for item in shared_themes]

    def identify_shared_emotions(self, search_ids):
        """Computes overlapping emotional vectors by averaging probability metrics"""
        emotion_vectors = []
        emotions_list = ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]

        for sid in search_ids:
            search = db.session.get(SearchHistory, sid)
            if not search:
                continue
            dist = search.aggregated_emotion_distribution
            if dist:
                vector = [float(dist.get(em, 0.0)) for em in emotions_list]
                emotion_vectors.append(vector)

        if not emotion_vectors:
            return {}

        avg_vector = np.mean(emotion_vectors, axis=0)
        shared_emotions = {emotions_list[i]: float(avg_vector[i]) for i in range(len(emotions_list))}
        return shared_emotions

    def identify_shared_narratives(self, search_ids):
        """Detects article pairs across different searches with cosine similarity exceeding 60%"""
        shared_claims = []
        searches_articles = {}

        # Load articles for each search ID
        for sid in search_ids:
            articles = db.session.query(Article).filter_by(search_id=sid).all()
            if articles:
                searches_articles[sid] = articles

        sids = list(searches_articles.keys())
        if len(sids) < 2:
            return []

        # Compare articles pairwise across searches
        for i in range(len(sids)):
            for j in range(i + 1, len(sids)):
                sid1, sid2 = sids[i], sids[j]
                arts1, arts2 = searches_articles[sid1], searches_articles[sid2]

                for a1 in arts1:
                    for a2 in arts2:
                        # Compute similarity
                        vectorizer = TfidfVectorizer(stop_words='english')
                        preprocessed = preprocess_texts_batch([a1.content, a2.content])
                        if not preprocessed[0].strip() or not preprocessed[1].strip():
                            continue
                        
                        try:
                            tfidf = vectorizer.fit_transform(preprocessed)
                            sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
                        except Exception:
                            sim = 0.0

                        if sim >= 0.60:
                            shared_claims.append({
                                "search_id_a": sid1,
                                "search_id_b": sid2,
                                "article_id_a": a1.id,
                                "article_id_b": a2.id,
                                "title_a": a1.title,
                                "title_b": a2.title,
                                "source_a": a1.source or "Unknown",
                                "source_b": a2.source or "Unknown",
                                "similarity_score": sim
                            })

        # Sort by similarity score descending and limit to top 25
        shared_claims = sorted(shared_claims, key=lambda x: x["similarity_score"], reverse=True)[:25]
        return shared_claims

    def calculate_cross_search_similarity(self, search_ids):
        """Combines text similarity (50%), emotional similarity (30%), and veracity ratings (20%) into overall 0-100 score"""
        n_searches = len(search_ids)
        if n_searches < 2:
            return 0.0

        # 1. Text Similarity (average pairwise similarity between searches' combined text corpora)
        combined_texts = []
        for sid in search_ids:
            articles = db.session.query(Article).filter_by(search_id=sid).all()
            combined_text = " ".join([a.content for a in articles])
            combined_texts.append(combined_text)

        text_sims = []
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            preprocessed = preprocess_texts_batch(combined_texts)
            # Filter out empty preprocessed texts
            valid_preprocessed = [txt if txt.strip() else "empty text" for txt in preprocessed]
            tfidf = vectorizer.fit_transform(valid_preprocessed)
            sim_matrix = cosine_similarity(tfidf)
            
            for i in range(n_searches):
                for j in range(i + 1, n_searches):
                    text_sims.append(sim_matrix[i, j])
        except Exception as e:
            current_app.logger.warning(f"Failed to calculate cross search text similarity: {str(e)}")
            text_sims = [0.0]

        avg_text_sim = float(np.mean(text_sims))

        # 2. Emotional Similarity (average pairwise cosine similarity of emotion distributions)
        emotions_list = ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]
        emotion_vectors = []
        for sid in search_ids:
            search = db.session.get(SearchHistory, sid)
            dist = search.aggregated_emotion_distribution if search else {}
            vec = [float(dist.get(em, 0.0)) for em in emotions_list]
            # Normalize vector to avoid division by zero
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = [v / norm for v in vec]
            emotion_vectors.append(vec)

        emotion_sims = []
        for i in range(n_searches):
            for j in range(i + 1, n_searches):
                # Cosine similarity of normalized vectors is dot product
                sim = float(np.dot(emotion_vectors[i], emotion_vectors[j]))
                emotion_sims.append(sim)

        avg_emotion_sim = float(np.mean(emotion_sims)) if emotion_sims else 0.0

        # 3. Veracity Rating Overlap (average pairwise rating match, 1 if match, 0 if mismatch)
        veracity_matches = []
        veracity_ratings = []
        for sid in search_ids:
            search = db.session.get(SearchHistory, sid)
            rating = search.fact_check_result if search else "UNAUDITED"
            veracity_ratings.append(rating)

        for i in range(n_searches):
            for j in range(i + 1, n_searches):
                match = 1.0 if veracity_ratings[i] == veracity_ratings[j] else 0.0
                veracity_matches.append(match)

        avg_veracity_sim = float(np.mean(veracity_matches)) if veracity_matches else 0.0

        # Combine weighted metrics (0-100 scale)
        overall_score = (avg_text_sim * 0.50 + avg_emotion_sim * 0.30 + avg_veracity_sim * 0.20) * 100.0
        return max(0.0, min(100.0, float(overall_score)))

    def generate_comparative_report(self, search_ids, user_id, report_name):
        """Generates a complete comparative report snapshot and writes to DB. Implements caching lookup."""
        # Clean and sort search IDs to maintain determinism
        sorted_ids = sorted(list(set(search_ids)))
        
        # 1. Check comparison validation limits
        if len(sorted_ids) < 2 or len(sorted_ids) > 10:
            raise ValueError("Comparative analysis requires between 2 and 10 search queries.")

        # 2. Caching lookup via unique comparison_hash
        ids_str = ",".join(map(str, sorted_ids))
        comp_hash = hashlib.sha256(ids_str.encode()).hexdigest()

        existing_report = ResearchReport.query.filter_by(comparison_hash=comp_hash, user_id=user_id).first()
        if existing_report:
            current_app.logger.info(f"Report comparison cache hit for hash: {comp_hash}")
            comparison = ComparisonResult.query.filter_by(report_id=existing_report.id).first()
            return existing_report, comparison, True

        # 3. Compute analytical values
        shared_themes = self.identify_shared_themes(sorted_ids)
        shared_emotions = self.identify_shared_emotions(sorted_ids)
        shared_claims = self.identify_shared_narratives(sorted_ids)
        similarity_score = self.calculate_cross_search_similarity(sorted_ids)

        # 4. Generate report explanation (Gemini vs Fallback)
        summary = self._generate_report_summary_text(
            search_ids=sorted_ids,
            similarity_score=similarity_score,
            themes=shared_themes,
            emotions=shared_emotions
        )

        # 5. Commit ResearchReport to Database (Snapshot mode)
        report = ResearchReport(
            user_id=user_id,
            report_name=report_name,
            summary=summary
        )
        report.search_ids = sorted_ids  # Triggers comparison_hash generation
        db.session.add(report)
        db.session.flush()  # Extract report.id for ComparisonResult mapping

        comparison = ComparisonResult(
            report_id=report.id,
            similarity_score=similarity_score
        )
        comparison.shared_themes = shared_themes
        comparison.shared_emotions = shared_emotions
        comparison.shared_claims = shared_claims
        db.session.add(comparison)

        try:
            db.session.commit()
            current_app.logger.info(f"Successfully created comparative report '{report_name}' (ID: {report.id})")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to persist comparative report: {str(e)}")
            raise e

        return report, comparison, False

    def _generate_report_summary_text(self, search_ids, similarity_score, themes, emotions):
        """Generates report summary text using Gemini with local fallbacks"""
        queries = []
        veracity_ratings = []
        for sid in search_ids:
            search = db.session.get(SearchHistory, sid)
            if search:
                queries.append(f"'{search.query}'")
                veracity_ratings.append(f"'{search.query}': {search.fact_check_result or 'UNAUDITED'}")

        queries_str = ", ".join(queries)
        ratings_str = "; ".join(veracity_ratings)
        top_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3]
        emotions_str = ", ".join([f"{k} ({v:.1f}%)" for k, v in top_emotions])

        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                current_app.logger.info("Generating comparative report summary via Gemini API...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = (
                    "You are a professional research intelligence analyst. Write a comprehensive comparative "
                    f"misinformation intelligence report (under 200 words) analyzing the relationship between "
                    f"these topics: {queries_str}.\n\n"
                    f"- Fact ratings: {ratings_str}\n"
                    f"- Computed cross-topic similarity score: {similarity_score:.1f}/100\n"
                    f"- Shared themes (keywords): {', '.join(themes)}\n"
                    f"- Aggregated shared emotional profiles: {emotions_str}\n\n"
                    "Synthesize the patterns of misinformation and emotional manipulation tactics. "
                    "Highlight any recurring narratives, common themes, and shared emotional vectors. "
                    "Make sure the report is objective and formal."
                )
                
                response = model.generate_content(prompt)
                if response and response.text:
                    current_app.logger.info("Successfully generated comparative report via Gemini API")
                    return response.text.strip()
            except Exception as e:
                current_app.logger.warning(f"Gemini comparative summary failed: {str(e)}. Using local fallback.")

        # Local fallback text
        current_app.logger.info("Using local fallback template for comparative summary...")
        summary = (
            f"Comparative research analysis between the queries {queries_str} reveals a cross-topic "
            f"similarity index of {similarity_score:.1f}/100. Factuality profiles show veracity classifications: "
            f"{ratings_str}. The semantic text collections share core thematic keywords including "
            f"{', '.join(themes)}. Emotional profiles aggregated across these topics indicate dominant shared "
            f"emotional vectors: {emotions_str}. These overlapping trends indicate structured thematic "
            f"similarities and common emotional manipulation strategies across the compared narratives."
        )
        return summary

    def export_report_to_json(self, report, comparison, profiles):
        """Exports the research report details to standard JSON structure"""
        return {
            "report_name": report.report_name,
            "comparison_hash": report.comparison_hash,
            "similarity_score": comparison.similarity_score,
            "summary": report.summary,
            "shared_themes": comparison.shared_themes,
            "shared_emotions": comparison.shared_emotions,
            "shared_claims": comparison.shared_claims,
            "search_profiles": profiles,
            "created_at": report.created_at.isoformat() if report.created_at else None
        }

    def export_report_to_html_printable(self, report, comparison, profiles):
        """Generates a beautifully formatted printable HTML document (PDF export fallback)"""
        profiles_html = ""
        for prof in profiles:
            profiles_html += f"""
            <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #f8fafc;">
                <h3 style="margin-top: 0; color: #4f46e5;">Topic: {prof['query']}</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr><td style="font-weight: bold; width: 40%; padding: 4px 0;">Fact verdict:</td><td>{prof['fact_check_verdict']}</td></tr>
                    <tr><td style="font-weight: bold; padding: 4px 0;">Dominant emotion:</td><td>{prof['overall_emotion']} ({prof['overall_risk_level']} Risk)</td></tr>
                    <tr><td style="font-weight: bold; padding: 4px 0;">Collected articles:</td><td>{prof['articles_count']}</td></tr>
                    <tr><td style="font-weight: bold; padding: 4px 0;">Date analyzed:</td><td>{prof['created_at']}</td></tr>
                </table>
            </div>
            """

        claims_html = ""
        for claim in comparison.shared_claims:
            claims_html += f"""
            <div style="padding: 10px; border-bottom: 1px solid #e2e8f0;">
                <div style="font-weight: bold; font-size: 13px;">{claim['title_a']} <span style="color: #64748b;">(Source: {claim['source_a']})</span></div>
                <div style="font-size: 13px; margin: 4px 0;">↔ {claim['title_b']} <span style="color: #64748b;">(Source: {claim['source_b']})</span></div>
                <div style="font-size: 11px; font-weight: bold; color: #4f46e5;">Similarity match: {claim['similarity_score'] * 100:.1f}%</div>
            </div>
            """

        if not claims_html:
            claims_html = "<p style='font-size: 13px; color: #64748b;'>No highly similar cross-search article pairs detected.</p>"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MET Research Intelligence Report - {report.report_name}</title>
    <style>
        body {{ font-family: 'Inter', system-ui, sans-serif; color: #1e293b; line-height: 1.5; padding: 30px; max-width: 800px; margin: 0 auto; }}
        h1 {{ font-size: 24px; font-weight: bold; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; color: #0f172a; margin-bottom: 5px; }}
        h2 {{ font-size: 16px; font-weight: bold; text-transform: uppercase; color: #4f46e5; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-top: 30px; }}
        .meta-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
        .meta-table td {{ padding: 6px; border: 1px solid #e2e8f0; }}
        .summary-box {{ border-left: 4px solid #4f46e5; background-color: #f1f5f9; padding: 15px; border-radius: 4px; font-size: 14px; font-weight: 500; }}
        .tag {{ display: inline-block; background-color: #e0e7ff; color: #4338ca; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-right: 6px; margin-bottom: 6px; }}
    </style>
</head>
<body>
    <h1>MET Research Intelligence Report</h1>
    <div style="font-size: 13px; font-weight: bold; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 25px;">
        Snapshot ID: {report.comparison_hash[:16]} • Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>

    <h2>Report Name</h2>
    <p style="font-size: 16px; font-weight: bold; margin-top: 5px;">{report.report_name}</p>

    <h2>Research Summary & Comparative Analysis</h2>
    <div class="summary-box">{report.summary}</div>

    <table class="meta-table">
        <tr><td style="font-weight: bold; width: 45%;">Cross-Search Similarity Score:</td><td style="font-weight: bold; color: #4f46e5;">{comparison.similarity_score:.1f}/100</td></tr>
        <tr><td style="font-weight: bold;">Number of searches compared:</td><td>{len(report.search_ids)}</td></tr>
    </table>

    <h2>Shared Themes (Keywords)</h2>
    <div style="margin: 15px 0;">
        {"".join([f'<span class="tag">{t}</span>' for t in comparison.shared_themes])}
    </div>

    <h2>Shared Emotional Manipulation Profile</h2>
    <table class="meta-table">
        {"".join([f"<tr><td style='font-weight: bold;'>{k}:</td><td>{v:.1f}%</td></tr>" for k, v in comparison.shared_emotions.items()])}
    </table>

    <h2>Shared Narratives & Clashing Claims</h2>
    <div style="margin-top: 15px;">
        {claims_html}
    </div>

    <h2>Search Profiles Compared</h2>
    <div style="margin-top: 15px;">
        {profiles_html}
    </div>

    <div style="margin-top: 40px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 15px;">
        MET Platform Research Division • Confidential Research Document
    </div>
</body>
</html>
"""
        return html
