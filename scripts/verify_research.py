import os
import sys
import unittest
import json
import time
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.report import ResearchReport, ComparisonResult

class Module6ResearchVerificationTest(unittest.TestCase):
    """Automated verification suite for Module 6 Research Intelligence."""

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
        
        # Clean up existing test tables
        db.session.query(ComparisonResult).delete()
        db.session.query(ResearchReport).delete()
        db.session.query(Article).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()
        
        # Create test users
        self.password = "Password123!"
        
        self.user_a_email = "usera_research@met.com"
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_research", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b_email = "userb_research@met.com"
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_research", email=self.user_b_email)
            self.user_b.set_password(self.password)
            db.session.add(self.user_b)
            
        db.session.commit()
        
        # Authenticate
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
        """Test API endpoints JWT protection and invalid format inputs"""
        print("\n--- TEST 1: JWT Protection & Routing Checks ---")
        
        # GET all reports (No Token) -> 401
        res = self.client.get('/api/research/reports')
        self.assertEqual(res.status_code, 401)
        
        # POST compare (No Token) -> 401
        res = self.client.post('/api/research/compare', json={"search_ids": [1, 2], "report_name": "Test"})
        self.assertEqual(res.status_code, 401)
        
        # GET report details (No Token) -> 401
        res = self.client.get('/api/research/report/1')
        self.assertEqual(res.status_code, 401)
        
        # GET report export (No Token) -> 401
        res = self.client.get('/api/research/report/1/export')
        self.assertEqual(res.status_code, 401)
        print("[OK] JWT Authorization controls verified across all routes.")

    def test_02_limits_validation(self):
        """Verify minimum of 2 and maximum of 10 search history items constraint"""
        print("\n--- TEST 2: Comparison Bounds Validation ---")
        
        # 1. Less than 2 search IDs
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [1],
            "report_name": "Too Few"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 2 and 10", res.json['message'])
        
        # 2. More than 10 search IDs
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": list(range(1, 12)),
            "report_name": "Too Many"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 2 and 10", res.json['message'])
        print("[OK] 2-10 searches validation limit functioning correctly.")

    def test_03_ownership_boundaries(self):
        """Verify cross-user ownership isolation is enforced strictly"""
        print("\n--- TEST 3: Cross-User Ownership Boundaries ---")
        
        # Create Search History under User B
        search_b1 = SearchHistory(user_id=self.user_b.id, query="User B Vaccine query 1", status="completed", search_status="completed")
        search_b2 = SearchHistory(user_id=self.user_b.id, query="User B Vaccine query 2", status="completed", search_status="completed")
        db.session.add_all([search_b1, search_b2])
        db.session.commit()
        
        # User A tries to compare User B's search histories
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [search_b1.id, search_b2.id],
            "report_name": "Stolen Data Report"
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found or access denied", res.json['message'])
        print("[OK] Cross-user search query inputs rejected with 404 Not Found.")

    def test_04_comparative_analytics_computation(self):
        """Verify full comparison calculation flow including Text, Emotion and Veracity Similarity"""
        print("\n--- TEST 4: Comparative Analytics Calculations ---")
        
        # Create searches and articles under User A
        s1 = SearchHistory(
            user_id=self.user_a.id, query="COVID-19 5G microchips myth", status="completed", search_status="completed",
            fact_check_result="FALSE", overall_emotion="Fear", overall_risk_level="HIGH"
        )
        s1.aggregated_emotion_distribution = {"Joy": 5.0, "Fear": 50.0, "Anger": 25.0, "Sadness": 10.0, "Love": 5.0, "Surprise": 5.0}
        
        s2 = SearchHistory(
            user_id=self.user_a.id, query="Vaccines contain nano trackers", status="completed", search_status="completed",
            fact_check_result="FALSE", overall_emotion="Fear", overall_risk_level="HIGH"
        )
        s2.aggregated_emotion_distribution = {"Joy": 5.0, "Fear": 45.0, "Anger": 30.0, "Sadness": 10.0, "Love": 5.0, "Surprise": 5.0}
        
        db.session.add_all([s1, s2])
        db.session.commit()
        
        # Add articles
        a1 = Article(
            search_id=s1.id, user_id=self.user_a.id, title="5G Towers emit mind control frequencies",
            content="The 5G towers are spreading microchips that track your mind and control you through radio waves. Severe panic is spreading.",
            url="https://a.com/1", source="a.com", content_hash="ch1"
        )
        a2 = Article(
            search_id=s2.id, user_id=self.user_a.id, title="Vaccines contain microchip nanobots",
            content="Doctors are injecting liquid microchip nanobots inside vaccines to track everyone globally. This is scary and people are very afraid.",
            url="https://b.com/2", source="b.com", content_hash="ch2"
        )
        db.session.add_all([a1, a2])
        db.session.commit()
        
        # Execute comparison
        t0 = time.time()
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [s1.id, s2.id],
            "report_name": "Vaccine Trackers Comparison"
        })
        duration = time.time() - t0
        print(f"Comparison report generated in {duration:.4f} seconds.")
        
        self.assertEqual(res.status_code, 200)
        data = res.json['data']
        self.assertFalse(data['cached'])
        self.assertEqual(data['report_name'], "Vaccine Trackers Comparison")
        self.assertIsNotNone(data['summary'])
        self.assertGreater(data['similarity_score'], 0.0)
        self.assertIn("microchip", [theme.lower() for theme in data['shared_themes']])
        self.assertIn("Fear", data['shared_emotions'])
        
        # Verify cached hit on second run
        res_cached = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [s1.id, s2.id],
            "report_name": "Vaccine Trackers Comparison Cached"
        })
        self.assertEqual(res_cached.status_code, 200)
        self.assertTrue(res_cached.json['data']['cached'])
        self.assertEqual(res_cached.json['data']['id'], data['id'])
        print("[OK] Full analytics (text, emotions, veracity) and cached hits validated.")

    def test_05_cascade_deletes(self):
        """Verify database cascade delete behavior for ResearchReport and ComparisonResult"""
        print("\n--- TEST 5: Database Cascade Deletes ---")
        
        s1 = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        s2 = SearchHistory(user_id=self.user_a.id, query="Q2", status="completed", search_status="completed")
        db.session.add_all([s1, s2])
        db.session.commit()
        
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [s1.id, s2.id],
            "report_name": "Cascade Delete Report"
        })
        self.assertEqual(res.status_code, 200)
        report_id = res.json['data']['id']
        
        # Check rows in DB
        rep_count = db.session.query(ResearchReport).filter_by(id=report_id).count()
        comp_count = db.session.query(ComparisonResult).filter_by(report_id=report_id).count()
        self.assertEqual(rep_count, 1)
        self.assertEqual(comp_count, 1)
        
        # Delete the ResearchReport
        report_obj = db.session.get(ResearchReport, report_id)
        db.session.delete(report_obj)
        db.session.commit()
        
        # Assert cascade delete
        comp_count_after = db.session.query(ComparisonResult).filter_by(report_id=report_id).count()
        self.assertEqual(comp_count_after, 0)
        print("[OK] Database cascade deletes function cleanly.")

    def test_06_exports(self):
        """Verify export to PDF/HTML and JSON formats"""
        print("\n--- TEST 6: Report Exports (JSON & Printable HTML) ---")
        
        s1 = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        s2 = SearchHistory(user_id=self.user_a.id, query="Q2", status="completed", search_status="completed")
        db.session.add_all([s1, s2])
        db.session.commit()
        
        res = self.client.post('/api/research/compare', headers=self.headers_a, json={
            "search_ids": [s1.id, s2.id],
            "report_name": "Export Report"
        })
        self.assertEqual(res.status_code, 200)
        report_id = res.json['data']['id']
        
        # Export as JSON
        res_json = self.client.get(f'/api/research/report/{report_id}/export?format=json', headers=self.headers_a)
        self.assertEqual(res_json.status_code, 200)
        self.assertIn("comparison_hash", res_json.json)
        self.assertIn("similarity_score", res_json.json)
        
        # Export as PDF (HTML)
        res_pdf = self.client.get(f'/api/research/report/{report_id}/export?format=pdf', headers=self.headers_a)
        self.assertEqual(res_pdf.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", res_pdf.data)
        self.assertIn(b"MET Research Intelligence Report", res_pdf.data)
        print("[OK] JSON & printable HTML report exports verify completely.")

if __name__ == "__main__":
    unittest.main()
