import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.sentiment import SentimentResult

class Module5AVerificationTest(unittest.TestCase):
    """Automated verification suite for Module 5A Sentiment Intelligence Engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['DEBUG'] = True
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Enforce foreign keys
        db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        db.session.rollback()
        
        # Clean up existing test users/searches
        db.session.query(SentimentResult).delete()
        db.session.query(Article).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()
        
        # Create test user
        self.username = "researcher_verify"
        self.email = "verify@met_platform.com"
        self.password = "Password123!"
        
        self.user = User.query.filter_by(email=self.email).first()
        if not self.user:
            self.user = User(username=self.username, email=self.email)
            self.user.set_password(self.password)
            db.session.add(self.user)
            db.session.commit()
            
        # Authenticate
        login_res = self.client.post('/api/auth/login', json={
            "email": self.email,
            "password": self.password
        })
        self.token = login_res.json['data']['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_01_complete_verification_flow(self):
        """Runs the complete verification flow for COVID vaccine infertility search query."""
        print("\n=== STEP 1: Executing Search Query 'COVID vaccine infertility' ===")
        search_res = self.client.post('/api/search', headers=self.headers, json={
            "query": "COVID vaccine infertility"
        })
        self.assertEqual(search_res.status_code, 200, "Search query failed.")
        search_data = search_res.json['data']
        search_id = search_data['id']
        articles_collected = search_data['articles_collected']
        print(f"[OK] Search history ID: {search_id}. Articles collected: {articles_collected}.")
        
        print("\n=== STEP 2: Executing POST /api/sentiment/analyze ===")
        analyze_res = self.client.post('/api/sentiment/analyze', headers=self.headers, json={
            "search_id": search_id
        })
        self.assertEqual(analyze_res.status_code, 200, "Sentiment analyze request failed.")
        
        res_payload = analyze_res.json
        self.assertTrue(res_payload['success'], "API returned success=False.")
        self.assertIn('data', res_payload, "API response is missing 'data' wrapper.")
        
        data = res_payload['data']
        self.assertFalse(data['cached'], "First run should not be cached.")
        self.assertEqual(data['search_id'], search_id)
        
        print("\n=== STEP 3 & 8: Verifying API Response Schema ===")
        self.assertIn('overall_emotion', data)
        self.assertIn('overall_risk_level', data)
        self.assertIn('emotion_distribution', data)
        self.assertIn('sentiment_analyzed_at', data)
        self.assertIn('articles', data)
        
        print(f"Overall Dominant Emotion: {data['overall_emotion']}")
        print(f"Overall Risk Level: {data['overall_risk_level']}")
        print(f"Aggregated Emotion Distribution: {data['emotion_distribution']}")
        
        print("\n=== STEP 4, 5 & 6: Verifying Article-Level Details & Risk Levels ===")
        articles = data['articles']
        self.assertGreater(len(articles), 0, "No articles analyzed.")
        
        for idx, art in enumerate(articles):
            print(f"\nVerifying Article {idx + 1}: '{art['title'][:40]}...'")
            self.assertIn('article_id', art)
            self.assertIn('dominant_emotion', art)
            self.assertIn('confidence', art)
            self.assertIn('emotion_distribution', art)
            self.assertIn('risk_level', art)
            self.assertIn('model_version', art)
            
            self.assertEqual(art['model_version'], "emotion_v1")
            
            # Verify distribution categories
            dist = art['emotion_distribution']
            for emotion in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]:
                self.assertIn(emotion, dist, f"Missing emotion category: {emotion}")
                self.assertIsInstance(dist[emotion], (int, float))
            
            # Verify sum equals 100%
            dist_sum = sum(dist.values())
            print(f"  Distribution sum: {dist_sum}%")
            self.assertAlmostEqual(dist_sum, 100.0, delta=1.5, msg="Emotion distribution percentages do not sum to 100%")
            
            # Verify risk level rules
            fear = dist.get("Fear", 0.0)
            anger = dist.get("Anger", 0.0)
            expected_risk = "LOW"
            if fear > 40.0 or (fear + anger) > 60.0:
                expected_risk = "HIGH"
            elif fear > 20.0 or (fear + anger) > 30.0:
                expected_risk = "MEDIUM"
                
            self.assertEqual(art['risk_level'], expected_risk, f"Incorrect risk level. Got {art['risk_level']}, expected {expected_risk} for Fear={fear}%, Anger={anger}%.")
            print(f"  Emotion: {art['dominant_emotion']} (confidence: {art['confidence']})")
            print(f"  Risk Level: {art['risk_level']} (Fear={fear}%, Anger={anger}%)")
            
        print("\n=== STEP 7: Verifying Database Persistence ===")
        # Verify SentimentResult rows in DB
        db_results = db.session.query(SentimentResult).filter_by(search_id=search_id).all()
        self.assertEqual(len(db_results), len(articles), "Database SentimentResult count mismatch.")
        
        for db_res in db_results:
            self.assertIsNotNone(db_res.dominant_emotion)
            self.assertIsNotNone(db_res.confidence)
            self.assertIsNotNone(db_res.risk_level)
            self.assertEqual(db_res.model_version, "emotion_v1")
            self.assertIsNotNone(db_res.emotions_json)
            
        # Verify SearchHistory aggregate cache
        updated_search = db.session.get(SearchHistory, search_id)
        self.assertEqual(updated_search.overall_emotion, data['overall_emotion'])
        self.assertEqual(updated_search.overall_risk_level, data['overall_risk_level'])
        self.assertIsNotNone(updated_search.sentiment_analyzed_at)
        print("[OK] All SentimentResult and SearchHistory cache fields verified in SQLite.")
        
        print("\n=== STEP 10: Verifying Cache Retrieval on Repeated Call ===")
        analyze_res_cached = self.client.post('/api/sentiment/analyze', headers=self.headers, json={
            "search_id": search_id
        })
        self.assertEqual(analyze_res_cached.status_code, 200)
        data_cached = analyze_res_cached.json['data']
        self.assertTrue(data_cached['cached'], "Second analyze call should hit the cache.")
        self.assertEqual(data_cached['overall_emotion'], data['overall_emotion'])
        self.assertEqual(data_cached['overall_risk_level'], data['overall_risk_level'])
        print("[OK] Cache hit verified successfully.")

if __name__ == "__main__":
    unittest.main()
