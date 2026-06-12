import os
import sys
import time
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.models.article import Article
from app.services.evolution_service import EvolutionService

def run_benchmarks():
    app = create_app()
    with app.app_context():
        print("Starting evolution engine benchmarks...")
        
        # 1. Prepare synthetic articles (10 articles of varying sizes)
        articles = []
        for i in range(1, 11):
            title = f"Article title {i} showing variant propagation"
            # Simulate shifting text content
            if i <= 3:
                content = "A rumor claims that vaccines cause infertility and increase pregnancy risks significantly."
            elif i <= 6:
                content = "Rumors spread claiming vaccines have pregnancy side effects, but some health experts say it requires study."
            else:
                content = "Official medical researchers and clinical trials confirm that vaccines are completely safe and have no links to infertility."
            
            art = MagicMock(spec=Article, id=i, title=title, content=content, source=f"news{i}.com", published_at=None, created_at=None)
            articles.append(art)
        
        # 2. Benchmark Vectorization & Similarity Matrix
        start = time.perf_counter()
        raw_contents = [art.content for art in articles]
        from app.services.nlp_service import preprocess_texts_batch
        preprocessed = preprocess_texts_batch(raw_contents)
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform(preprocessed)
        sim = cosine_similarity(tfidf)
        t_vectorization = (time.perf_counter() - start) * 1000.0
        
        # 3. Benchmark Clustering
        start = time.perf_counter()
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        dist_matrix = np.clip(1.0 - sim, 0.0, 1.0)
        clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=0.4, metric='precomputed', linkage='average')
        labels = clustering.fit_predict(dist_matrix)
        t_clustering = (time.perf_counter() - start) * 1000.0
        
        # 4. Benchmark Drift Calculation
        start = time.perf_counter()
        baseline_sims = sim[0, 1:]
        drift_vals = 1.0 - baseline_sims
        drift_score = np.mean(drift_vals) * 100.0
        t_drift = (time.perf_counter() - start) * 1000.0
        
        # 5. Benchmark Theme Extraction
        start = time.perf_counter()
        feature_names = vectorizer.get_feature_names_out()
        sums = np.asarray(tfidf.sum(axis=0)).flatten()
        top_indices = sums.argsort()[::-1][:10]
        themes = [feature_names[idx] for idx in top_indices]
        t_themes = (time.perf_counter() - start) * 1000.0
        
        # 6. Benchmark Mutation Detection
        start = time.perf_counter()
        mutation_points = []
        for i in range(1, len(articles)):
            similarity = sim[i - 1, i]
            if similarity < 0.85:
                mutation_points.append(i)
        t_mutations = (time.perf_counter() - start) * 1000.0
        
        # 7. Benchmark Local Summary Generator
        start = time.perf_counter()
        svc = EvolutionService()
        fallback_summary = svc._generate_evolution_summary(articles, drift_score, "Moderate Drift", len(set(labels)), themes)
        t_summary_local = (time.perf_counter() - start) * 1000.0
        
        # 8. Complete analyze pipeline
        start = time.perf_counter()
        full_res = svc.analyze_evolution(articles)
        t_pipeline = (time.perf_counter() - start) * 1000.0
        
        print("\n--- Benchmark Timings (10 Documents) ---")
        print(f"Text Processing & TF-IDF Similarity Matrix: {t_vectorization:.3f} ms")
        print(f"Agglomerative Clustering:                 {t_clustering:.3f} ms")
        print(f"Narrative Drift Score Calculation:        {t_drift:.3f} ms")
        print(f"Theme Feature Weight Extraction:           {t_themes:.3f} ms")
        print(f"Mutation Point Timeline Traversals:       {t_mutations:.3f} ms")
        print(f"Local Fallback Summary Generation:        {t_summary_local:.3f} ms")
        print(f"Total Service analyze_evolution Pipeline: {t_pipeline:.3f} ms")

if __name__ == '__main__':
    run_benchmarks()
