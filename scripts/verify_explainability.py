import os
import sys
import time
import json
from datetime import datetime

# Adjust search path to locate the Flask application
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.explainability import ExplainabilityResult
from app.services.explainability_service import ExplainabilityService

def verify_and_benchmark():
    app = create_app()
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-123'
    
    print("=" * 60)
    print("STARTING MODULE 10: EXPLAINABILITY & MODEL GOVERNANCE AUDIT")
    print("=" * 60)
    
    with app.app_context():
        # Setup Test Sandbox Database Records
        db.create_all()
        
        # 1. Fetch or create test user
        test_user = User.query.filter_by(email="xai_test@met.org").first()
        if not test_user:
            test_user = User(email="xai_test@met.org", username="xai_tester")
            test_user.set_password("SecurePass123!")
            db.session.add(test_user)
            db.session.commit()
            
        test_user_2 = User.query.filter_by(email="xai_tester_2@met.org").first()
        if not test_user_2:
            test_user_2 = User(email="xai_tester_2@met.org", username="xai_tester_2")
            test_user_2.set_password("SecurePass123!")
            db.session.add(test_user_2)
            db.session.commit()

        # 2. Setup mock search query and articles
        search = SearchHistory(
            user_id=test_user.id,
            query="Vaccine Microchip conspiratorial hoax",
            fact_check_result="MISINFORMATION DETECTED",
            search_status="completed"
        )
        db.session.add(search)
        db.session.commit()
        
        art1 = Article(
            search_id=search.id,
            user_id=test_user.id,
            url="https://fakenewsconspiracy.com/microchips-inside",
            title="Evidence of Microchips in Vaccination Vials",
            content="Shocking breakthrough reports indicate nano transmitters in medical vials.",
            source="fakenewsconspiracy.com"
        )
        art2 = Article(
            search_id=search.id,
            user_id=test_user.id,
            url="https://nejm.org/vaccine-study-facts",
            title="Comprehensive Trial of Vaccination Veracity",
            content="Rigorous peer-reviewed study confirms complete safety without additives.",
            source="nejm.org"
        )
        db.session.add(art1)
        db.session.add(art2)
        db.session.commit()

        # Clear existing XAI snapshots for this query
        ExplainabilityResult.query.filter_by(search_id=search.id).delete()
        db.session.commit()

        # 3. Test ExplainabilityService Generation & Benchmarking
        service = ExplainabilityService()
        
        print("\n[TEST 1] Testing Service-level XAI Generation (Cache Miss)...")
        start_time = time.perf_counter()
        miss_res = service.generate_search_explainability(search.id, force_refresh=True)
        miss_duration = (time.perf_counter() - start_time) * 1000.0
        
        print(f"-> Cache Miss Duration: {miss_duration:.2f} ms")
        assert miss_res["cached"] is False, "First call must not indicate cached snapshot"
        assert miss_res["confidence"] > 0.0, "Confidence score must be populated"
        assert miss_res["confidence_level"] in ("Very Low", "Low", "Medium", "High", "Very High"), "Confidence level mapping failed"
        
        # Verify structure
        exp = miss_res["explanation"]
        assert "Executive Summary" in exp, "Executive Summary key missing in narrative"
        assert "Supporting Evidence" in exp, "Supporting Evidence key missing"
        assert "Overall Recommendation" in exp, "Overall Recommendation missing"
        
        # Verify Feature Importance schema
        assert len(miss_res["feature_importance"]) > 0, "Feature importances list empty"
        for fi in miss_res["feature_importance"]:
            assert "feature" in fi and "importance" in fi and "direction" in fi, "Feature importance invalid schema"
            
        print("-> Cache Miss Validation: PASSED")

        # 4. Benchmarking Cache Hit
        print("\n[TEST 2] Testing Caching Mechanics (Cache Hit Benchmark)...")
        start_time = time.perf_counter()
        hit_res = service.generate_search_explainability(search.id, force_refresh=False)
        hit_duration = (time.perf_counter() - start_time) * 1000.0
        
        print(f"-> Cache Hit Duration: {hit_duration:.2f} ms")
        assert hit_res["cached"] is True, "Second call must hit the cache"
        assert hit_res["id"] == miss_res["id"], "Cached ID mismatch"
        print("-> Caching Verification: PASSED")
        
        # 5. Model Versioning & Registry Governance Integrity
        print("\n[TEST 3] Testing Governance Model Registry Metadata...")
        assert hit_res["model_name"] == "MET Hybrid Verification & Risk Classifier", "Model name incorrect"
        assert hit_res["model_version"] == "xai_v1.0", "Model version missing"
        assert hit_res["vectorizer_version"] == "tfidf_v1.0", "Vectorizer version missing"
        assert hit_res["pipeline_version"] == "met_pipeline_v1.0", "Pipeline version missing"
        assert "processing_time_ms" in hit_res, "Processing latency tracker missing"
        print("-> Model Version Tracking: PASSED")

    # 6. Test Flask API Client & Ownership Isolation
    print("\n[TEST 4] Testing JWT Authentication and Cross-User Access Isolation...")
    with app.test_client() as client:
        # Get Auth Token for User 1
        login_res = client.post('/api/auth/login', json={
            "email": "xai_test@met.org",
            "password": "SecurePass123!"
        })
        token_1 = login_res.get_json()["data"]["access_token"]

        # Get Auth Token for User 2
        login_res_2 = client.post('/api/auth/login', json={
            "email": "xai_tester_2@met.org",
            "password": "SecurePass123!"
        })
        token_2 = login_res_2.get_json()["data"]["access_token"]

        # A. Attempt request without token (Must return 401)
        res_no_auth = client.get(f'/api/explainability/search/{search.id}')
        assert res_no_auth.status_code == 401, f"Unauthorized request returned {res_no_auth.status_code}"
        print("-> JWT Protection: PASSED")

        # B. User 1 requests their own record (Must return 200)
        res_user_1 = client.get(
            f'/api/explainability/search/{search.id}',
            headers={'Authorization': f'Bearer {token_1}'}
        )
        assert res_user_1.status_code == 200, f"Owner fetch request returned {res_user_1.status_code}"
        print("-> Owner Access Authorization: PASSED")

        # C. User 2 requests User 1's record (Must return 404 for isolation)
        res_user_2 = client.get(
            f'/api/explainability/search/{search.id}',
            headers={'Authorization': f'Bearer {token_2}'}
        )
        assert res_user_2.status_code == 404, f"Cross-user request returned {res_user_2.status_code} (Expected 404)"
        print("-> Cross-User Resource Isolation: PASSED")

        # D. Clean up database sandbox objects
        with app.app_context():
            # Cascade deletes verification: deleting search must cascade delete explainability
            print("\n[TEST 5] Testing Cascade Deletes Constraints...")
            db.session.delete(search)
            db.session.commit()
            
            check_xai = ExplainabilityResult.query.filter_by(search_id=search.id).first()
            assert check_xai is None, "Cascade delete failed: ExplainabilityResult record orphaned"
            print("-> Cascade Delete Constraints: PASSED")

            # Final Cleanup of Sandbox users
            db.session.delete(test_user)
            db.session.delete(test_user_2)
            db.session.commit()

    print("\n" + "=" * 60)
    print("ALL MODULE 10 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    verify_and_benchmark()
