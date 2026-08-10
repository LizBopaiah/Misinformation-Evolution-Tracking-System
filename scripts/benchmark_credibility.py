import os
import sys
import time

sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.services.credibility_service import CredibilityService
from app.models.credibility import SourceCredibility, SourceCredibilityHistory

def run_benchmarks():
    app = create_app()
    with app.app_context():
        # Clear database records to ensure cache miss
        db.session.query(SourceCredibilityHistory).delete()
        db.session.query(SourceCredibility).delete()
        db.session.commit()

        svc = CredibilityService()
        domain = "benchmarkdomain.com"

        print("--- Running Module 9 Performance Benchmarks ---")

        # 1. Benchmark Cache Miss
        start_time = time.time()
        res_miss = svc.calculate_credibility(domain)
        miss_duration = (time.time() - start_time) * 1000.0
        print(f"Cache Miss Duration (Calculation + Save): {miss_duration:.2f} ms")

        # 2. Benchmark Cache Hit
        start_time = time.time()
        res_hit = svc.calculate_credibility(domain)
        hit_duration = (time.time() - start_time) * 1000.0
        print(f"Cache Hit Duration (Retrieve from DB Cache): {hit_duration:.2f} ms")

        # 3. Clean up
        db.session.query(SourceCredibilityHistory).delete()
        db.session.query(SourceCredibility).delete()
        db.session.commit()

if __name__ == "__main__":
    run_benchmarks()
