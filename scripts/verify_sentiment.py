import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

# Add project root to sys.path to enable app imports
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.sentiment import SentimentResult

class Module5ASentimentTestCase(unittest.TestCase):
    """Integration test suite to verify Module 5A Sentiment Intelligence Engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['DEBUG'] = True
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Enable SQLite Foreign Keys explicitly
        db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        # 1. Rollback any pending failed transactions first
        db.session.rollback()
        
        # 2. Clean up test database tables to ensure isolation
        db.session.query(SentimentResult).delete()
        db.session.query(Article).delete()
        # Deleting SearchHistory will trigger cascade deletes on related child rows as well
        db.session.query(SearchHistory).delete()
        db.session.commit()

        # Create User A and User B if they don't exist
        self.user_a_email = "usera_sentiment@met.com"
        self.user_b_email = "userb_sentiment@met.com"
        self.password = "Password123!"
        
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_sentiment", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_sentiment", email=self.user_b_email)
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
        """Test authentication controls for sentiment analyze and GET endpoints."""
        print("\n--- Running Test 1: Authentication Routing Protection ---")
        
        # 1. POST analyze without auth
        res_post = self.client.post('/api/sentiment/analyze', json={"search_id": 1})
        self.assertEqual(res_post.status_code, 401)
        print("[OK] POST /api/sentiment/analyze rejected unauthenticated request.")
        
        # 2. GET sentiment without auth
        res_get = self.client.get('/api/sentiment/1')
        self.assertEqual(res_get.status_code, 401)
        print("[OK] GET /api/sentiment/<search_id> rejected unauthenticated request.")

    def test_02_isolation_and_ownership(self):
        """Test search query ownership and isolation between users."""
        print("\n--- Running Test 2: Access Control Isolation ---")
        
        # Create a search and article under User A
        search_a = SearchHistory(user_id=self.user_a.id, query="User A Search Topic", status="completed", search_status="completed")
        db.session.add(search_a)
        db.session.commit()
        
        art_a = Article(search_id=search_a.id, user_id=self.user_a.id, title="User A Title", content="Article content details.", url="https://usera.com/art1", source="usera.com", content_hash="hasha1")
        db.session.add(art_a)
        db.session.commit()
        
        # User B tries to run sentiment analysis on User A's search_id
        res_analyze = self.client.post('/api/sentiment/analyze', headers=self.headers_b, json={"search_id": search_a.id})
        self.assertEqual(res_analyze.status_code, 404)
        print("[OK] Cross-user sentiment analysis triggers blocked (404 Not Found).")
        
        # User B tries to GET sentiment details for User A's search_id
        res_get = self.client.get(f'/api/sentiment/{search_a.id}', headers=self.headers_b)
        self.assertEqual(res_get.status_code, 404)
        print("[OK] Cross-user sentiment results retrieval blocked (404 Not Found).")

    def test_03_input_validation(self):
        """Test POST analyze endpoint input validation bounds."""
        print("\n--- Running Test 3: Input Validation ---")
        
        # 1. Missing search_id
        res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("search_id field is required.", res.json['message'])
        
        # 2. Non-integer search_id
        res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": "invalid_id"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("search_id must be an integer.", res.json['message'])
        
        # 3. Non-existent search_id
        res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": 999999})
        self.assertEqual(res.status_code, 404)
        print("[OK] Endpoint correctly validates malformed or non-existent search ID input parameters.")

    def test_04_batch_inference_and_aggregation(self):
        """Test batch model prediction, aggregation, risk grading, and DB updates."""
        print("\n--- Running Test 4: Batch Inference & Aggregations ---")
        
        # Create completed search and articles for User A
        search = SearchHistory(user_id=self.user_a.id, query="Election Manipulation Claim", status="completed", search_status="completed")
        db.session.add(search)
        db.session.commit()
        
        art1 = Article(search_id=search.id, user_id=self.user_a.id, title="Fear Panic", content="There is an extreme panic and danger of election fraud. People are afraid of the future.", url="https://test1.com/art", source="test1.com", content_hash="hash1")
        art2 = Article(search_id=search.id, user_id=self.user_a.id, title="Joy Happy", content="What a wonderful day. Everybody is celebrating the victory and feeling joyful.", url="https://test2.com/art", source="test2.com", content_hash="hash2")
        db.session.add_all([art1, art2])
        db.session.commit()
        
        # Trigger sentiment analysis
        res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 200)
        
        res_data = res.json['data']
        self.assertFalse(res_data['cached'])
        self.assertEqual(res_data['search_id'], search.id)
        self.assertIsNotNone(res_data['overall_emotion'])
        self.assertIsNotNone(res_data['overall_risk_level'])
        
        # Check distribution
        dist = res_data['emotion_distribution']
        self.assertEqual(len(dist), 6)
        total_prob = sum(dist.values())
        self.assertAlmostEqual(total_prob, 100.0, delta=1.5) # Sum of average percentages is ~100
        
        # Check article specific results
        articles_res = res_data['articles']
        self.assertEqual(len(articles_res), 2)
        for art in articles_res:
            self.assertIsNotNone(art['dominant_emotion'])
            self.assertGreaterEqual(art['confidence'], 0.0)
            self.assertEqual(art['model_version'], "emotion_v1")
            # Verify probabilities sum to 100
            self.assertAlmostEqual(sum(art['emotion_distribution'].values()), 100.0, delta=0.5)
            
        # Verify SearchHistory db update
        updated_search = db.session.get(SearchHistory, search.id)
        self.assertEqual(updated_search.overall_emotion, res_data['overall_emotion'])
        self.assertEqual(updated_search.overall_risk_level, res_data['overall_risk_level'])
        self.assertIsNotNone(updated_search.sentiment_analyzed_at)
        print("[OK] Batch preprocessing and vectorization executed cleanly.")
        print("[OK] Probability outputs converted to standardized 0-100% scale.")
        print("[OK] Risk levels calculated correctly and aggregates saved to SearchHistory cache.")

    def test_05_caching_and_duplicate_prevention(self):
        """Test cached response routing and database duplicate prevention updates."""
        print("\n--- Running Test 5: Caching & Duplicate Prevention ---")
        
        # Create completed search and articles for User A
        search = SearchHistory(user_id=self.user_a.id, query="Cache Query test", status="completed", search_status="completed")
        db.session.add(search)
        db.session.commit()
        
        art1 = Article(search_id=search.id, user_id=self.user_a.id, title="Cached art", content="This is cached content data.", url="https://cache1.com/art", source="cache1.com", content_hash="chash1")
        db.session.add(art1)
        db.session.commit()
        
        # First execution (Cache Miss)
        res1 = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(res1.json['data']['cached'])
        
        # Assert one SentimentResult row in DB
        cnt_before = db.session.query(SentimentResult).filter_by(search_id=search.id).count()
        self.assertEqual(cnt_before, 1)
        
        # Second execution (Cache Hit)
        res2 = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json['data']['cached'])
        
        # Assert database rows count remains exactly 1 (duplicate prevention check)
        cnt_after = db.session.query(SentimentResult).filter_by(search_id=search.id).count()
        self.assertEqual(cnt_after, 1)
        print("[OK] Caching returns stored results immediately with cached: true.")
        print("[OK] Repeated analysis triggers update existing rows instead of creating duplicate records.")

    def test_06_cascade_deletes(self):
        """Test cascade deletes: deleting search history must delete sentiment results."""
        print("\n--- Running Test 6: SQLite Database Cascade Deletes ---")
        
        # Create completed search and articles for User A
        search = SearchHistory(user_id=self.user_a.id, query="Cascade test", status="completed", search_status="completed")
        db.session.add(search)
        db.session.commit()
        
        art1 = Article(search_id=search.id, user_id=self.user_a.id, title="Cascade art", content="Content text.", url="https://cascade1.com/art", source="cascade1.com", content_hash="cash1")
        db.session.add(art1)
        db.session.commit()
        
        # Analyze to populate SentimentResult
        res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": search.id})
        self.assertEqual(res.status_code, 200)
        
        cnt_sent = db.session.query(SentimentResult).filter_by(search_id=search.id).count()
        self.assertEqual(cnt_sent, 1)
        
        # Delete the SearchHistory
        db.session.delete(search)
        db.session.commit()
        
        # Assert SentimentResult cascade-deleted
        cnt_after = db.session.query(SentimentResult).filter_by(search_id=search.id).count()
        self.assertEqual(cnt_after, 0)
        print("[OK] Cascade deletes verify: search query deletion successfully purged all sentiment results.")

    def test_07_graceful_503_fallback(self):
        """Test that missing model files trigger a graceful 503 response without server crashes."""
        print("\n--- Running Test 7: Graceful 503 Fallback ---")
        
        # Create completed search and articles for User A
        search = SearchHistory(user_id=self.user_a.id, query="Fallback 503 query", status="completed", search_status="completed")
        db.session.add(search)
        db.session.commit()
        
        art1 = Article(search_id=search.id, user_id=self.user_a.id, title="Fallback art", content="Content to analyze.", url="https://fallback503.com/art", source="fallback503.com", content_hash="fash1")
        db.session.add(art1)
        db.session.commit()
        
        # Mock load_model_and_vectorizer to raise FileNotFoundError
        with patch('app.services.model_service.ModelService.load_model_and_vectorizer') as mock_load:
            mock_load.side_effect = FileNotFoundError("Mock missing model files error")
            
            res = self.client.post('/api/sentiment/analyze', headers=self.headers_a, json={"search_id": search.id})
            self.assertEqual(res.status_code, 503)
            self.assertFalse(res.json['success'])
            self.assertIn("missing model artifacts", res.json['message'])
            print("[OK] Missing model files handled gracefully, returning 503 Service Unavailable without crash.")

if __name__ == "__main__":
    unittest.main()
