import os
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from flask import current_app
from app.services.nlp_service import preprocess_texts_batch

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class EvolutionService:
    """Service to analyze, cluster, and track the evolution of narratives over time"""

    # Similarity thresholds from Module 5B design specifications
    SAME_NARRATIVE_THRESHOLD = 0.85
    MODIFIED_NARRATIVE_THRESHOLD = 0.60

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                current_app.logger.error(f"Failed to configure Gemini API in EvolutionService: {str(e)}")

    def analyze_evolution(self, articles):
        """
        Main analysis pipeline:
        1. Timelines ordering: Sort articles chronologically
        2. Text preprocessing & vectorization
        3. Cosine similarity calculation
        4. Clustering using AgglomerativeClustering
        5. Narrative drift calculation
        6. Theme extraction (top 10 keywords)
        7. Mutation point detection
        8. Summary generation
        """
        if not articles:
            raise ValueError("No articles provided for analysis.")

        # 1. Timeline Ordering (Fallback order: published_at, created_at, id)
        def sort_key(art):
            pub = getattr(art, 'published_at', None)
            if pub:
                return (0, pub, art.id)
            created = getattr(art, 'created_at', None)
            if created:
                return (1, created, art.id)
            return (2, getattr(art, 'id', 0), art.id)

        sorted_articles = sorted(articles, key=sort_key)
        baseline_art = sorted_articles[0]
        n_docs = len(sorted_articles)

        # 2. Text Preprocessing & TF-IDF Vectorization
        raw_contents = [art.content for art in sorted_articles]
        preprocessed_contents = preprocess_texts_batch(raw_contents)
        
        # Guard against empty preprocessed texts
        valid_preprocessed = [txt for txt in preprocessed_contents if txt.strip()]
        if not valid_preprocessed:
            # If preprocessing stripped everything, fallback to raw contents
            valid_preprocessed = [txt if txt.strip() else "empty text" for txt in raw_contents]

        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(valid_preprocessed)

        # 3. Cosine Similarity Matrix
        sim_matrix = cosine_similarity(tfidf_matrix)

        # 4. Clustering (AgglomerativeClustering using cosine distance)
        # Cosine distance = 1 - Cosine Similarity
        dist_matrix = np.clip(1.0 - sim_matrix, 0.0, 1.0)
        
        if n_docs > 1:
            try:
                # Group into clusters where members have similarity >= 60% (distance <= 0.4)
                clustering = AgglomerativeClustering(
                    n_clusters=None,
                    distance_threshold=0.4,
                    metric='precomputed',
                    linkage='average'
                )
                cluster_labels = clustering.fit_predict(dist_matrix)
                # Convert numpy types to python int
                cluster_labels = [int(lbl) for lbl in cluster_labels]
            except Exception as e:
                current_app.logger.warning(f"Clustering failed: {str(e)}. Defaulting all to cluster 0.")
                cluster_labels = [0] * n_docs
        else:
            cluster_labels = [0]

        # Count total variants
        total_variants = len(set(cluster_labels))

        # 5. Narrative Drift Score
        # Average(1 - similarity_with_baseline) * 100
        if n_docs > 1:
            baseline_similarities = sim_matrix[0, 1:]
            drift_values = 1.0 - baseline_similarities
            drift_score = float(np.mean(drift_values) * 100.0)
            # Clip drift score within [0, 100]
            drift_score = max(0.0, min(100.0, drift_score))
        else:
            drift_score = 0.0

        # Interpret Drift Score
        if drift_score <= 20.0:
            drift_label = "Stable Narrative"
        elif drift_score <= 50.0:
            drift_label = "Moderate Drift"
        else:
            drift_label = "Significant Mutation"

        # 6. Theme Extraction (Top 10 overall keywords by summed TF-IDF importance)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_sums = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
        top_indices = tfidf_sums.argsort()[::-1][:10]
        top_themes = [str(feature_names[idx]) for idx in top_indices]

        # Identify dominant narrative (e.g. from the largest cluster, or baseline title)
        # We can find the most common cluster label
        cluster_counts = {}
        for lbl in cluster_labels:
            cluster_counts[lbl] = cluster_counts.get(lbl, 0) + 1
        dominant_cluster = max(cluster_counts, key=cluster_counts.get)
        
        # Find the title of the first article in the dominant cluster
        dominant_narrative = next(
            (sorted_articles[i].title for i, lbl in enumerate(cluster_labels) if lbl == dominant_cluster),
            baseline_art.title
        )

        # 7. Mutation Point Detection
        # Compare consecutive articles in the chronological timeline
        mutation_points = []
        for i in range(1, n_docs):
            prev_art = sorted_articles[i - 1]
            curr_art = sorted_articles[i]
            # Similarity between consecutive documents
            similarity = float(sim_matrix[i - 1, i])
            
            if similarity < self.SAME_NARRATIVE_THRESHOLD:
                # Determine mutation type description
                if similarity >= self.MODIFIED_NARRATIVE_THRESHOLD:
                    mutation_type = "Modified Narrative"
                    reason = f"Similarity dropped to {similarity:.1%} (Moderate narrative shift)."
                else:
                    mutation_type = "New Narrative Variant"
                    reason = f"Similarity dropped to {similarity:.1%} (Significant mutation/new variant)."
                
                mutation_points.append({
                    "from_article_id": prev_art.id,
                    "from_title": prev_art.title,
                    "to_article_id": curr_art.id,
                    "to_title": curr_art.title,
                    "similarity_score": similarity,
                    "mutation_type": mutation_type,
                    "reason": reason
                })

        # Build detailed Timeline JSON
        timeline = []
        for i, art in enumerate(sorted_articles):
            sim_to_base = float(sim_matrix[0, i])
            timeline.append({
                "article_id": art.id,
                "title": art.title,
                "source": art.source or "Unknown",
                "published_at": art.published_at.isoformat() if art.published_at else (art.created_at.isoformat() if art.created_at else None),
                "similarity_to_baseline": sim_to_base,
                "cluster_label": cluster_labels[i],
                "is_baseline": i == 0
            })

        # 8. Summary Generation
        summary = self._generate_evolution_summary(
            sorted_articles=sorted_articles,
            drift_score=drift_score,
            drift_label=drift_label,
            total_variants=total_variants,
            themes=top_themes
        )

        return {
            "baseline_article_id": baseline_art.id,
            "narrative_drift_score": drift_score,
            "total_variants_detected": total_variants,
            "dominant_narrative": dominant_narrative,
            "evolution_summary": summary,
            "mutation_points": mutation_points,
            "timeline": timeline
        }

    def _generate_evolution_summary(self, sorted_articles, drift_score, drift_label, total_variants, themes):
        """Generates evolution summary using Gemini with a local fallback"""
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                current_app.logger.info("Generating narrative evolution summary via Gemini API...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Format timeline list for the prompt
                timeline_text = ""
                for idx, art in enumerate(sorted_articles):
                    pub_str = art.published_at.strftime("%Y-%m-%d") if art.published_at else "Unknown Date"
                    timeline_text += f"{idx + 1}. [{pub_str}] {art.title}: {art.content[:200]}...\n\n"

                prompt = (
                    "You are a professional misinformation analyst. Write a unified, concise narrative "
                    "evolution report (under 150 words) tracing how this story has mutated over time. "
                    f"The analysis has computed a narrative drift score of {drift_score:.1f}/100 ({drift_label}) "
                    f"across {len(sorted_articles)} articles, resulting in {total_variants} distinct variants. "
                    f"The top emerging themes are: {', '.join(themes)}.\n\n"
                    "Timeline of articles:\n"
                    f"{timeline_text}"
                )
                
                response = model.generate_content(prompt)
                if response and response.text:
                    current_app.logger.info("Successfully generated evolution summary via Gemini API")
                    return response.text.strip()
            except Exception as e:
                current_app.logger.warning(f"Gemini evolution summary generation failed: {str(e)}. Using local fallback.")

        # Local template-based fallback
        current_app.logger.info("Using local template fallback for evolution summary...")
        baseline_title = sorted_articles[0].title
        latest_title = sorted_articles[-1].title if len(sorted_articles) > 1 else baseline_title
        
        summary = (
            f"The narrative sequence initiated with '{baseline_title}'. Over time, the discussion "
            f"developed into {total_variants} narrative variant{'s' if total_variants > 1 else ''} with a "
            f"narrative drift score of {drift_score:.1f}/100, indicating {drift_label.lower()}. "
            f"The primary emerging themes identified across the text corpus are: {', '.join(themes)}. "
            f"The narrative path concludes with discussions surrounding '{latest_title}'."
        )
        return summary

