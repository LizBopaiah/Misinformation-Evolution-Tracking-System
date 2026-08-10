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
from app.models.credibility import SourceCredibility, SourceCredibilityHistory
from app.services.credibility_service import CredibilityService

class Module9CredibilityTestCase(unittest.TestCase):
    """Integration test suite to verify Module 9 Source Credibility & Trust Scoring Engine."""

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
        db.session.rollback()
        
        # Clean up test database tables
        db.session.query(SourceCredibilityHistory).delete()
        db.session.query(SourceCredibility).delete()
        db.session.query(Article).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()

        # Create test users
        self.user_a_email = "usera_credibility@met.com"
        self.user_b_email = "userb_credibility@met.com"
        self.password = "Password123!"
        
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_credibility", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_credibility", email=self.user_b_email)
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

    def test_01_domain_normalization(self):
        """Test url extraction and normalization details using tldextract"""
        print("\n--- Running Test 1: Domain Normalization ---")
        svc = CredibilityService()
        
        # Standard domains
        self.assertEqual(svc.normalize_domain("https://www.reuters.com/news/123"), "reuters.com")
        self.assertEqual(svc.normalize_domain("http://nih.gov/path?query=1"), "nih.gov")
        
        # Subdomains normalization
        self.assertEqual(svc.normalize_domain("https://subdomain.google.co.uk/test/page.html"), "google.co.uk")
        self.assertEqual(svc.normalize_domain("http://www.science.org/"), "science.org")
        
        # Empty/invalid fallbacks
        self.assertEqual(svc.normalize_domain(""), "unknown")
        print("[OK] Domain normalizations match expected targets cleanly.")

    def test_02_credibility_weighting_and_grades(self):
        """Test weighted calculations and exact letter grade mapping bands"""
        print("\n--- Running Test 2: Credibility Scores and Grade Mapping ---")
        svc = CredibilityService()
        
        # Gov/Edu bonus and high reputation scores
        gov_cred = svc.calculate_credibility("cdc.gov")
        self.assertGreaterEqual(gov_cred['credibility_score'], 90.0)
        self.assertEqual(gov_cred['letter_grade'], "A+")
        
        # Standard defaults (70 base reputation + other defaults -> ~76.0 B/C)
        normal_cred = svc.calculate_credibility("testdomain.com")
        self.assertEqual(normal_cred['letter_grade'], "C")
        
        # Low trust mapping (breitbart.com -> 30 reputation -> low score/F)
        low_cred = svc.calculate_credibility("breitbart.com")
        self.assertEqual(low_cred['letter_grade'], "F")
        
        # Exact Grade Maps Validation
        self.assertEqual(svc.get_letter_grade(96.0), "A+")
        self.assertEqual(svc.get_letter_grade(91.0), "A")
        self.assertEqual(svc.get_letter_grade(83.0), "B")
        self.assertEqual(svc.get_letter_grade(75.0), "C")
        self.assertEqual(svc.get_letter_grade(62.0), "D")
        self.assertEqual(svc.get_letter_grade(50.0), "F")
        print("[OK] Credibility logic maps letter grades and applies bonuses correctly.")

    def test_03_historical_reliability_tracking(self):
        """Test logging of subsequent domain lookups and rolling history averages"""
        print("\n--- Running Test 3: Historical Tracking and Rolling Averages ---")
        svc = CredibilityService()
        
        # Insert first run
        res1 = svc.calculate_credibility("rollingtest.com")
        self.assertEqual(res1['analysis_count'], 1)
        
        # Insert second run
        res2 = svc.calculate_credibility("rollingtest.com", force=True)
        self.assertEqual(res2['analysis_count'], 2)
        
        # Check history rows populated
        parent = SourceCredibility.query.filter_by(domain="rollingtest.com").first()
        self.assertEqual(len(parent.history), 2)
        print("[OK] Historical count incremented and updates recorded in historical log table.")

    def test_04_caching_behavior(self):
        """Test database query caching bypass on repeated requests"""
        print("\n--- Running Test 4: Credibility Database Query Caching ---")
        svc = CredibilityService()
        
        # Initial run (triggers full calculation)
        svc.calculate_credibility("cachedomain.com")
        
        # Call again without force (should load cached)
        # We check by patching to verify the db commit is skipped
        with patch('app.extensions.db.session.commit') as mock_commit:
            svc.calculate_credibility("cachedomain.com")
            mock_commit.assert_not_called()
            
        print("[OK] Cache lookup returns existing domain rating immediately without database commits.")

    def test_05_api_protection_and_boundaries(self):
        """Test endpoints access protection and invalid request boundaries"""
        print("\n--- Running Test 5: JWT Protection and API Access Boundaries ---")
        
        # 1. GET domain credibility without auth
        res_get = self.client.get('/api/credibility/cdc.gov')
        self.assertEqual(res_get.status_code, 401)
        
        # 2. POST recalculate without auth
        res_post = self.client.post('/api/credibility/recalculate', json={"domain": "cdc.gov"})
        self.assertEqual(res_post.status_code, 401)
        
        # 3. GET domain credibility with auth
        res_get_auth = self.client.get('/api/credibility/cdc.gov', headers=self.headers_a)
        self.assertEqual(res_get_auth.status_code, 200)
        self.assertEqual(res_get_auth.json['data']['domain'], "cdc.gov")
        
        # 4. Malformed domain payload validation
        res_malformed = self.client.post('/api/credibility/recalculate', headers=self.headers_a, json={})
        self.assertEqual(res_malformed.status_code, 400)
        
        # 5. Invalid character injection validation
        res_injection = self.client.get('/api/credibility/cdc.gov/../../../badpath', headers=self.headers_a)
        self.assertEqual(res_injection.status_code, 404) # Routing blocks traversal
        print("[OK] API endpoints protected and input parameters validate correctly.")

    def test_06_database_integrity_and_cascades(self):
        """Test database cascades: deleting credibility deletes child history log entries"""
        print("\n--- Running Test 6: SQLite Cascading Deletes ---")
        svc = CredibilityService()
        
        # Populate records
        svc.calculate_credibility("cascadedomain.com")
        svc.calculate_credibility("cascadedomain.com", force=True)
        
        parent = SourceCredibility.query.filter_by(domain="cascadedomain.com").first()
        parent_id = parent.id
        self.assertEqual(SourceCredibilityHistory.query.filter_by(source_credibility_id=parent_id).count(), 2)
        
        # Delete parent credibility
        db.session.delete(parent)
        db.session.commit()
        
        # Verify history is purged
        self.assertEqual(SourceCredibilityHistory.query.filter_by(source_credibility_id=parent_id).count(), 0)
        print("[OK] Foreign key constraints purge child history logs on parent domain score removals.")

    def test_07_search_integration(self):
        """Test automatic injection of credibility attributes during search queries"""
        print("\n--- Running Test 7: Automatic Search Integration ---")
        
        # Create Search and Articles
        search = SearchHistory(user_id=self.user_a.id, query="Vaccines study", status="completed", search_status="completed")
        db.session.add(search)
        db.session.commit()
        
        art = Article(search_id=search.id, user_id=self.user_a.id, title="NIH report", content="Study confirms findings.", url="https://nih.gov/study1", source="nih.gov")
        db.session.add(art)
        db.session.commit()
        
        # Request search details
        res = self.client.get(f'/api/search/{search.id}', headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        
        # Verify credibility scores are injected
        res_data = res.json['data']
        self.assertIsNotNone(res_data.get('average_source_credibility_score'))
        self.assertEqual(res_data.get('average_source_letter_grade'), "A+")
        
        articles = res_data['articles']
        self.assertEqual(len(articles), 1)
        self.assertIsNotNone(articles[0].get('source_credibility_score'))
        self.assertEqual(articles[0].get('source_letter_grade'), "A+")
        print("[OK] Credibility statistics successfully injected into search details payload.")

if __name__ == "__main__":
    unittest.main()
