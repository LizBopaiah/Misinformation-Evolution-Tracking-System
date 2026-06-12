import os
import sys
import unittest
import json
import time
import hashlib
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.fact_check import FactCheckResult
from app.models.export import ExportRecord

class Module7ExportsVerificationTest(unittest.TestCase):
    """Automated integration test suite to verify Module 7 Exports & Dossier System"""

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
        
        # Clean up database tables
        db.session.query(ExportRecord).delete()
        db.session.query(FactCheckResult).delete()
        db.session.query(Article).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()
        
        # Create test users
        self.password = "Password123!"
        
        self.user_a_email = "usera_exports@met.com"
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_exports", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b_email = "userb_exports@met.com"
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_exports", email=self.user_b_email)
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

    def test_01_jwt_protection(self):
        """Test API endpoints JWT protection"""
        print("\n--- TEST 1: JWT Protection Check ---")
        
        res = self.client.post('/api/export/fact-audit', json={})
        self.assertEqual(res.status_code, 401)
        
        res = self.client.get('/api/export/history')
        self.assertEqual(res.status_code, 401)
        
        res = self.client.get('/api/export/1')
        self.assertEqual(res.status_code, 401)
        
        res = self.client.delete('/api/export/1')
        self.assertEqual(res.status_code, 401)
        print("[OK] JWT checks verified.")

    def test_02_ownership_boundaries(self):
        """Test that a user cannot access another user's exports or search histories"""
        print("\n--- TEST 2: Ownership Boundary Guardrails ---")
        
        # Search History under User B
        s_b = SearchHistory(user_id=self.user_b.id, query="User B Secret Topic", status="completed", search_status="completed")
        db.session.add(s_b)
        db.session.commit()
        
        # User A tries to export User B's search history
        res = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={
            "search_id": s_b.id,
            "format": "pdf"
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found or access denied", res.json['message'])
        print("[OK] User-bound authorization isolation verified.")

    def test_03_pdf_json_html_generation_and_caching(self):
        """Test compiling fact audit, sentiment, evolution in PDF, JSON, HTML formats and cache reuse"""
        print("\n--- TEST 3: Compilers and Caching Verification ---")
        
        # Create completed search and articles for User A
        s = SearchHistory(
            user_id=self.user_a.id, query="Vaccines Cause Infertility", status="completed", search_status="completed",
            summary="Extracted narrative summaries.", fact_check_result="MISINFORMATION DETECTED"
        )
        db.session.add(s)
        db.session.commit()
        
        art = Article(
            search_id=s.id, user_id=self.user_a.id, title="Vaccines infertility myth",
            content="Article content claiming vaccines contain harmful tracking components.",
            url="https://myth1.com/infertility", source="myth1.com"
        )
        db.session.add(art)
        db.session.commit()
        
        # Generate PDF Dossier
        res = self.client.post('/api/export/dossier', headers=self.headers_a, json={
            "search_id": s.id,
            "format": "pdf"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json['data']
        self.assertEqual(data['export_format'], 'pdf')
        self.assertEqual(data['status'], 'completed')
        self.assertIsNotNone(data['file_hash'])
        self.assertGreater(data['file_size'], 0)
        
        pdf_export_id = data['id']
        
        # Check cache reuse (requesting again should return identical record instantly)
        res_cached = self.client.post('/api/export/dossier', headers=self.headers_a, json={
            "search_id": s.id,
            "format": "pdf"
        })
        self.assertEqual(res_cached.status_code, 200)
        self.assertEqual(res_cached.json['data']['id'], pdf_export_id)
        
        # Verify JSON export (needs sleep to bypass rate limit for fresh generation)
        time.sleep(5)
        res_json = self.client.post('/api/export/dossier', headers=self.headers_a, json={
            "search_id": s.id,
            "format": "json"
        })
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.json['data']['export_format'], 'json')
        
        # Verify HTML export (needs sleep to bypass rate limit for fresh generation)
        time.sleep(5)
        res_html = self.client.post('/api/export/dossier', headers=self.headers_a, json={
            "search_id": s.id,
            "format": "html"
        })
        self.assertEqual(res_html.status_code, 200)
        self.assertEqual(res_html.json['data']['export_format'], 'html')
        print("[OK] PDF, JSON, HTML compilers & caching operations verified.")

    def test_04_rate_limiting(self):
        """Test rate limit protection (max 1 request/5s, max 50/day)"""
        print("\n--- TEST 4: Abuse & Rate Limit Prevention ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        # Trigger export 1
        res1 = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "pdf"})
        self.assertEqual(res1.status_code, 200)
        
        # Trigger export 2 immediately (within 5 seconds) -> should return 429
        res2 = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "json"})
        self.assertEqual(res2.status_code, 429)
        self.assertIn("Rate limit exceeded", res2.json['message'])
        print("[OK] 5-second frequency limit correctly returns 429 Too Many Requests.")

    def test_05_oversized_dossier_rejection(self):
        """Test that dossier request fails if articles count exceeds 100 limit"""
        print("\n--- TEST 5: Oversized Dossier Rejection ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Oversized", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        # Add 101 articles
        for idx in range(101):
            art = Article(
                search_id=s.id, user_id=self.user_a.id, title=f"Art {idx}", content="Article Content.",
                url=f"https://x.com/{idx}", source="x.com", content_hash=f"ch_{idx}"
            )
            db.session.add(art)
        db.session.commit()
        
        # Request Dossier
        res = self.client.post('/api/export/dossier', headers=self.headers_a, json={
            "search_id": s.id,
            "format": "pdf"
        })
        self.assertEqual(res.status_code, 500)
        self.assertIn("Maximum dossier size exceeded", res.json['message'])
        print("[OK] Oversized dossiers rejected correctly to protect memory resources.")

    def test_06_sha256_verification_and_corruption_block(self):
        """Test SHA256 integrity checks and download blockage on mismatch"""
        print("\n--- TEST 6: Integrity Check & Corruption Handling ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        res = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "json"})
        self.assertEqual(res.status_code, 200)
        record_id = res.json['data']['id']
        
        # Load record
        record = db.session.get(ExportRecord, record_id)
        
        # Corrupt file on disk (write dummy content)
        with open(record.file_path, 'w', encoding='utf-8') as f:
            f.write("Corrupted data string here")
            
        # Download file -> should return 400 due to SHA256 mismatch
        res_dl = self.client.get(f'/api/export/{record_id}', headers=self.headers_a)
        self.assertEqual(res_dl.status_code, 400)
        self.assertIn("Integrity verification failed", res_dl.json['message'])
        print("[OK] Corrupted downloads blocked successfully.")

    def test_07_recovery_via_snapshot_json(self):
        """Test automatic file recovery from snapshot_json if deleted on disk"""
        print("\n--- TEST 7: Auto-Recovery from Database Snapshots ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        res = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "json"})
        self.assertEqual(res.status_code, 200)
        record_id = res.json['data']['id']
        record = db.session.get(ExportRecord, record_id)
        
        # Delete file from disk
        if os.path.exists(record.file_path):
            os.remove(record.file_path)
            
        # Download file -> should automatically regenerate using snapshot_json and stream successfully
        res_dl = self.client.get(f'/api/export/{record_id}', headers=self.headers_a)
        self.assertEqual(res_dl.status_code, 200)
        self.assertTrue(os.path.exists(record.file_path))
        print("[OK] Automatic file regeneration from DB snapshot validated.")

    def test_08_search_deletion_cascade_protection(self):
        """Verify deleting SearchHistory preserves ExportRecords and files"""
        print("\n--- TEST 8: Cascade Deletion Protection ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        res = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "json"})
        self.assertEqual(res.status_code, 200)
        record_id = res.json['data']['id']
        record = db.session.get(ExportRecord, record_id)
        
        # Delete search query
        db.session.delete(s)
        db.session.commit()
        
        # Verify ExportRecord still exists, source_id is set to None (or remains set to Null)
        updated_rec = db.session.get(ExportRecord, record_id)
        self.assertIsNotNone(updated_rec)
        self.assertTrue(os.path.exists(record.file_path))
        
        # Download still works
        res_dl = self.client.get(f'/api/export/{record_id}', headers=self.headers_a)
        self.assertEqual(res_dl.status_code, 200)
        print("[OK] SearchHistory deletion cascade protection verified successfully.")

    def test_09_export_history_and_deletion(self):
        """Test retrieving export history and deleting exports"""
        print("\n--- TEST 9: Export History & Deletes ---")
        
        s = SearchHistory(user_id=self.user_a.id, query="Q1", status="completed", search_status="completed")
        db.session.add(s)
        db.session.commit()
        
        res = self.client.post('/api/export/fact-audit', headers=self.headers_a, json={"search_id": s.id, "format": "json"})
        self.assertEqual(res.status_code, 200)
        record_id = res.json['data']['id']
        record = db.session.get(ExportRecord, record_id)
        
        # History
        res_hist = self.client.get('/api/export/history', headers=self.headers_a)
        self.assertEqual(res_hist.status_code, 200)
        self.assertGreater(len(res_hist.json['data']['history']), 0)
        
        # Delete
        res_del = self.client.delete(f'/api/export/{record_id}', headers=self.headers_a)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(os.path.exists(record.file_path))
        self.assertIsNone(db.session.get(ExportRecord, record_id))
        print("[OK] Archive history list and record deletion operations verified.")

if __name__ == "__main__":
    unittest.main()
