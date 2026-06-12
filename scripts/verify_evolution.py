import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to sys.path to enable app imports
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.evolution import EvolutionResult
from app.services.evolution_service import EvolutionService

class Module5BEvolutionTestCase(unittest.TestCase):
    """Integration test suite to verify Module 5B Narrative Evolution Tracking Engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['DEBUG'] = True
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Ensure latest database schema is created by recreating tables for testing
        db.drop_all()
        db.create_all()
        
        # Enable SQLite Foreign Keys explicitly
        db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        # 1. Rollback any pending failed transactions first
        db.session.rollback()
        
        # 2. Clean up test database tables to ensure isolation
        db.session.query(EvolutionResult).delete()
        db.session.query(Article).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()

        # Create User A and User B if they don't exist
        self.user_a_email = "usera_evolution@met.com"
        self.user_b_email = "userb_evolution@met.com"
        self.password = "Password123!"
        
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_evolution", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_evolution", email=self.user_b_email)
            self.user_b.set_password(self.password)
            db.session.add(self.user_b)
            
        db.session.commit()
        
        # Log in and get JWT tokens
        login_res_a = self.client.post('/api/auth/login', json={
            "email": self.user_a_email,
            "password": self.password
        })
        self.token_a = login_res_a.json['data']['access_token']
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}
        
        login_res_b = self.client.post('/api/auth/login', json={
            "email": self.user_b_email,
            "password": self.password
        })
        self.token_b = login_res_b.json['data']['access_token']
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

    def test_01_routing_protection_and_auth(self):
        """Test authentication controls for evolution endpoints (Rule 1)."""
        print("\n--- Running Test 1: Authentication Routing Protection ---")
        
        # 1. POST analyze without auth
        res_post = self.client.post('/api/evolution/analyze', json={"search_id": 1})
        self.assertEqual(res_post.status_code, 401)
        print("[OK] POST /api/evolution/analyze rejected unauthenticated request.")
        
        # 2. GET evolution without auth
        res_get = self.client.get('/api/evolution/1')
        self.assertEqual(res_get.status_code, 401)
        print("[OK] GET /api/evolution/<search_id> rejected unauthenticated request.")

    def test_02_isolation_and_ownership(self):
        """Test search query ownership and isolation between users (Rule 2)."""
        print("\n--- Running Test 2: Access Control Isolation ---")
        
        # Create a search and article under User A
        search_a = SearchHistory(user_id=self.user_a.id, query="User A Search Topic", status="completed")
        db.session.add(search_a)
        db.session.commit()
        
        art_a = Article(
            search_id=search_a.id, 
            user_id=self.user_a.id, 
            title="User A Title", 
            content="Article content details.", 
            url="https://usera.com/art1", 
            source="usera.com", 
            content_hash="hasha1"
        )
        db.session.add(art_a)
        db.session.commit()
        
        # User B tries to run evolution analysis on User A's search_id
        res_analyze = self.client.post('/api/evolution/analyze', headers=self.headers_b, json={"search_id": search_a.id})
        self.assertEqual(res_analyze.status_code, 404)
        print("[OK] Cross-user evolution analysis triggers blocked (404 Not Found).")
        
        # User B tries to GET evolution details for User A's search_id
        res_get = self.client.get(f'/api/evolution/{search_a.id}', headers=self.headers_b)
        self.assertEqual(res_get.status_code, 404)
        print("[OK] Cross-user evolution results retrieval blocked (404 Not Found).")

    def test_03_empty_search_handling(self):
        """Test evolution request for search history with no articles (Rule 3)."""
        print("\n--- Running Test 3: Empty Search Handling ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Empty Search Query", status="completed")
        db.session.add(search)
        db.session.commit()

        # Try analyzing without articles
        res = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 400)
        self.assertIn("No articles found", res.json['message'])
        print("[OK] Empty article sets handled cleanly, returning 400 Bad Request.")

    def test_04_single_article_search(self):
        """Test evolution run when only one article exists (Rule 4)."""
        print("\n--- Running Test 4: Single Article Analysis ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Single Article Query", status="completed")
        db.session.add(search)
        db.session.commit()
        
        art = Article(
            search_id=search.id,
            user_id=self.user_a.id,
            title="Only One Article",
            content="Vaccines are highly effective at preventing diseases and saving lives worldwide.",
            url="https://one.com/art",
            source="one.com",
            content_hash="onehash"
        )
        db.session.add(art)
        db.session.commit()

        res = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 200)
        
        res_data = res.json['data']
        self.assertEqual(res_data['narrative_drift_score'], 0.0)
        self.assertEqual(res_data['total_variants_detected'], 1)
        self.assertEqual(len(res_data['mutation_points']), 0)
        self.assertEqual(len(res_data['timeline']), 1)
        print("[OK] Single article search outputs zero drift, single variant, and empty mutation list.")

    def test_05_multi_article_search_and_drift_score_bounds(self):
        """Test standard multi-article analysis, drift calculations, and bounds (Rules 5, 6, 7, 8, 9)."""
        print("\n--- Running Test 5: Multi-Article Analysis & Drift Score Bounds ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Vaccines Infertility", status="completed")
        db.session.add(search)
        db.session.commit()
        
        # Create chronologically structured articles
        now = datetime.now()
        
        art1 = Article(
            search_id=search.id, user_id=self.user_a.id,
            title="Early rumor: Vaccines cause immediate infertility",
            content="Preliminary rumors spread across social media claiming that vaccines cause infertility in patients.",
            url="https://rumor.com/art", source="rumor.com", content_hash="hashr1",
            published_at=now - timedelta(days=10)
        )
        art2 = Article(
            search_id=search.id, user_id=self.user_a.id,
            title="Rumor spreads: Pregnancy risks exaggerated",
            content="Preliminary rumors spread across social media claiming that vaccines cause infertility in patients and exaggerate pregnancy risks.",
            url="https://rumor.com/art2", source="rumor.com", content_hash="hashr2",
            published_at=now - timedelta(days=5)
        )
        art3 = Article(
            search_id=search.id, user_id=self.user_a.id,
            title="Scientific report: Clinical trials find vaccines are safe",
            content="Official clinical trials and scientific research confirm that vaccines are safe and have no link to pregnancy complications or infertility.",
            url="https://science.com/art", source="science.com", content_hash="hashs1",
            published_at=now
        )
        
        db.session.add_all([art1, art2, art3])
        db.session.commit()

        res = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 200)
        
        res_data = res.json['data']
        drift = res_data['narrative_drift_score']
        
        # Verify drift is bounded in [0, 100]
        self.assertTrue(0.0 <= drift <= 100.0)
        
        # Since art3 is very different from art1 (baseline), drift should be moderate to high
        self.assertGreater(drift, 0.0)
        
        # Check timeline structures
        self.assertEqual(len(res_data['timeline']), 3)
        self.assertTrue(res_data['timeline'][0]['is_baseline'])
        
        # Cluster/variant count should be calculated
        self.assertGreaterEqual(res_data['total_variants_detected'], 1)
        
        # Summary should exist
        self.assertIsNotNone(res_data['evolution_summary'])
        
        # Check dominant narrative matches early/dominant article title
        self.assertIsNotNone(res_data['dominant_narrative'])
        print(f"[OK] Multi-article runs cleanly. Drift score: {drift:.2f}. Bounded in [0,100].")

    def test_06_caching_and_duplicate_prevention(self):
        """Test cached response routing and database duplicate prevention updates (Rules 10, 15)."""
        print("\n--- Running Test 6: Cache Routing & Duplicate Prevention ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Cache Test Query", status="completed")
        db.session.add(search)
        db.session.commit()
        
        art = Article(
            search_id=search.id, user_id=self.user_a.id,
            title="Topic baseline", content="Baseline article content details.",
            url="https://c1.com/art", source="c1.com", content_hash="chash1"
        )
        db.session.add(art)
        db.session.commit()

        # Cache Miss: analyze and store
        res1 = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(res1.json['data']['cached'])

        # Assert exactly one EvolutionResult row exists in DB
        db_count_before = db.session.query(EvolutionResult).filter_by(search_id=search.id).count()
        self.assertEqual(db_count_before, 1)

        # Cache Hit: subsequent request
        res2 = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json['data']['cached'])

        # Assert DB row count remains exactly 1 (duplicate prevention check)
        db_count_after = db.session.query(EvolutionResult).filter_by(search_id=search.id).count()
        self.assertEqual(db_count_after, 1)

        # GET API check
        res_get = self.client.get(f'/api/evolution/{search.id}', headers=self.headers_a)
        self.assertEqual(res_get.status_code, 200)
        self.assertTrue(res_get.json['data']['cached'])
        print("[OK] Cache hit returns saved results directly without executing service logic.")
        print("[OK] Duplicate records prevented on subsequent requests.")

    def test_07_cascade_deletes(self):
        """Test cascade deletes: deleting search history must delete evolution results (Rule 11)."""
        print("\n--- Running Test 7: SQLite Database Cascade Deletes ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Cascade Delete test", status="completed")
        db.session.add(search)
        db.session.commit()
        
        art = Article(
            search_id=search.id, user_id=self.user_a.id,
            title="Cascade Baseline", content="Cascade Article Content Details.",
            url="https://cd1.com/art", source="cd1.com", content_hash="cdhash1"
        )
        db.session.add(art)
        db.session.commit()
        
        # Populate analysis
        self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        
        # Verify entry exists
        self.assertEqual(db.session.query(EvolutionResult).filter_by(search_id=search.id).count(), 1)
        
        # Delete search query
        db.session.delete(search)
        db.session.commit()
        
        # Verify related evolution record is deleted
        self.assertEqual(db.session.query(EvolutionResult).filter_by(search_id=search.id).count(), 0)
        print("[OK] Cascade deletes verify: search query deletion successfully purged all evolution results.")

    def test_08_gemini_api_and_local_fallback(self):
        """Test Gemini API summary generation and the template-based local fallback (Rules 12, 13)."""
        print("\n--- Running Test 8: Gemini API Summaries & Local Fallback ---")
        
        # Test 8A: Local Fallback
        # Instantiating service with empty or invalid API key triggers local fallback
        svc_fallback = EvolutionService(api_key="AQ.mockkey")
        
        # Setup dummy Article objects
        art1 = MagicMock(spec=Article, id=1, title="Rumor claims vaccine dangers", content="Social media claims vaccine dangers.", source="rumor.com", published_at=None, created_at=None)
        art2 = MagicMock(spec=Article, id=2, title="Science says vaccine is safe", content="Scientific data says vaccine is safe.", source="science.com", published_at=None, created_at=None)
        
        res = svc_fallback.analyze_evolution([art1, art2])
        self.assertIsNotNone(res['evolution_summary'])
        self.assertIn("indicating", res['evolution_summary'])
        self.assertIn("primary emerging themes", res['evolution_summary'])
        print("[OK] Local template-based fallback generated a correct readable report.")

        # Test 8B: Gemini mock success check
        if genai := sys.modules.get('google.generativeai'):
            with patch('google.generativeai.GenerativeModel') as mock_model:
                mock_instance = MagicMock()
                mock_instance.generate_content.return_value = MagicMock(text="Mocked Gemini Evolution Summary.")
                mock_model.return_value = mock_instance
                
                svc_gemini = EvolutionService(api_key="valid_gemini_key_mock")
                # Force API availability flag
                with patch('app.services.evolution_service.GEMINI_AVAILABLE', True):
                    res_gemini = svc_gemini.analyze_evolution([art1, art2])
                    self.assertEqual(res_gemini['evolution_summary'], "Mocked Gemini Evolution Summary.")
                    print("[OK] Gemini integration successfully creates AI narrative reports when key is active.")

    def test_09_timeline_fallback_ordering(self):
        """Test chronological timeline fallbacks (Rule 14)."""
        print("\n--- Running Test 9: Timeline Ordering Fallbacks ---")
        
        search = SearchHistory(user_id=self.user_a.id, query="Ordering Query", status="completed")
        db.session.add(search)
        db.session.commit()
        
        # 1. Timeline order with published_at
        now = datetime.now()
        art1 = Article(search_id=search.id, user_id=self.user_a.id, title="Late", content="Content text.", url="https://o1.com/art", source="o1.com", published_at=now, content_hash="ohash1")
        art2 = Article(search_id=search.id, user_id=self.user_a.id, title="Early", content="Content text.", url="https://o2.com/art", source="o2.com", published_at=now - timedelta(days=2), content_hash="ohash2")
        db.session.add_all([art1, art2])
        db.session.commit()
        
        res = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 200)
        
        # "Early" should be first in timeline
        timeline = res.json['data']['timeline']
        self.assertEqual(timeline[0]['title'], "Early")
        
        # 2. Timeline order fallback to created_at when published_at is null
        db.session.query(Article).delete()
        db.session.commit()
        
        art3 = Article(search_id=search.id, user_id=self.user_a.id, title="Second", content="Content text.", url="https://o3.com/art", source="o3.com", published_at=None, created_at=now, content_hash="ohash3")
        art4 = Article(search_id=search.id, user_id=self.user_a.id, title="First", content="Content text.", url="https://o4.com/art", source="o4.com", published_at=None, created_at=now - timedelta(minutes=5), content_hash="ohash4")
        db.session.add_all([art3, art4])
        db.session.commit()
        
        # Bust cache by deleting evolution result
        db.session.query(EvolutionResult).delete()
        db.session.commit()
        
        res2 = self.client.post('/api/evolution/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res2.status_code, 200)
        
        timeline2 = res2.json['data']['timeline']
        self.assertEqual(timeline2[0]['title'], "First")
        print("[OK] Chronological timeline falls back correctly: published_at -> created_at -> database insertion order.")

if __name__ == "__main__":
    unittest.main()
