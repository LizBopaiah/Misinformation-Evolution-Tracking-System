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
from app.models.sentiment import SentimentResult
from app.models.evolution import EvolutionResult
from app.models.report import ResearchReport
from app.models.export import ExportRecord
from app.models.article import Article
from app.models.case import InvestigationCase, CaseItem, CaseActivity

class Module8CasesVerificationTest(unittest.TestCase):
    """Automated integration test suite to verify Module 8 Cases Workspace & Management"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        db.session.rollback()
        
        # Clean case and artifact tables
        db.session.query(CaseItem).delete()
        db.session.query(CaseActivity).delete()
        db.session.query(InvestigationCase).delete()
        db.session.query(ExportRecord).delete()
        db.session.query(ResearchReport).delete()
        db.session.query(EvolutionResult).delete()
        db.session.query(SentimentResult).delete()
        db.session.query(SearchHistory).delete()
        db.session.commit()

        # Create test users
        self.password = "Password123!"
        self.user_a_email = "usera_cases@met.com"
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_cases", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)

        self.user_b_email = "userb_cases@met.com"
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_cases", email=self.user_b_email)
            self.user_b.set_password(self.password)
            db.session.add(self.user_b)
        db.session.commit()

        # Login and obtain tokens
        login_res_a = self.client.post('/api/auth/login', json={"email": self.user_a_email, "password": self.password})
        self.token_a = login_res_a.json['data']['access_token']
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

        login_res_b = self.client.post('/api/auth/login', json={"email": self.user_b_email, "password": self.password})
        self.token_b = login_res_b.json['data']['access_token']
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

    def test_01_auth_protection(self):
        """Test API endpoints return 401 for unauthenticated requests"""
        print("\n--- TEST 1: JWT Protection Check ---")
        
        res = self.client.post('/api/cases', json={})
        self.assertEqual(res.status_code, 401)

        res = self.client.get('/api/cases')
        self.assertEqual(res.status_code, 401)

        res = self.client.get('/api/cases/1')
        self.assertEqual(res.status_code, 401)

        res = self.client.put('/api/cases/1', json={})
        self.assertEqual(res.status_code, 401)

        res = self.client.delete('/api/cases/1')
        self.assertEqual(res.status_code, 401)
        print("[OK] Auth validation verified.")

    def test_02_ownership_isolation(self):
        """Test that User B cannot access User A's case container (returns 404)"""
        print("\n--- TEST 2: Ownership Boundary Guardrails ---")
        
        # User A case
        case_a = InvestigationCase(user_id=self.user_a.id, title="User A Secret Case")
        db.session.add(case_a)
        db.session.commit()

        # User B attempts to fetch Case A
        res = self.client.get(f'/api/cases/{case_a.id}', headers=self.headers_b)
        self.assertEqual(res.status_code, 404)
        print("[OK] Ownership isolation boundary verified.")

    def test_03_crud_operations(self):
        """Test full Case CRUD lifecycle"""
        print("\n--- TEST 3: Case CRUD Lifecycle ---")
        
        # 1. Create Case
        res_create = self.client.post('/api/cases', headers=self.headers_a, json={
            "title": "Malaria Treatment Hoax",
            "description": "Investigating false cures.",
            "priority": "HIGH"
        })
        self.assertEqual(res_create.status_code, 201)
        case_id = res_create.json['data']['id']

        # 2. Retrieve Case
        res_get = self.client.get(f'/api/cases/{case_id}', headers=self.headers_a)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json['data']['case_details']['title'], "Malaria Treatment Hoax")

        # 3. Update Case
        res_update = self.client.put(f'/api/cases/{case_id}', headers=self.headers_a, json={
            "title": "Malaria Treatment Hoax - Updated",
            "priority": "CRITICAL"
        })
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json['data']['title'], "Malaria Treatment Hoax - Updated")
        self.assertEqual(res_update.json['data']['priority'], "CRITICAL")

        # 4. Soft Archive Case
        res_archive = self.client.delete(f'/api/cases/{case_id}', headers=self.headers_a)
        self.assertEqual(res_archive.status_code, 200)
        
        # Re-fetch and check ARCHIVED status
        res_get_archived = self.client.get(f'/api/cases/{case_id}', headers=self.headers_a)
        self.assertEqual(res_get_archived.json['data']['case_details']['status'], "ARCHIVED")
        print("[OK] CRUD operations validated.")

    def test_04_item_linking_and_uniqueness(self):
        """Test attaching various artifacts to case, unique constraints, and metadata snapshots"""
        print("\n--- TEST 4: Artifact Linking & Unique Constraints ---")
        
        case = InvestigationCase(user_id=self.user_a.id, title="Cases Hub", status="OPEN")
        db.session.add(case)
        db.session.commit()

        # Create SearchHistory artifact
        s = SearchHistory(user_id=self.user_a.id, query="Vaccines contain metal", search_status="completed")
        db.session.add(s)
        db.session.commit()

        # Link search artifact to case
        res_link = self.client.post(f'/api/cases/{case.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": s.id
        })
        self.assertEqual(res_link.status_code, 200)
        self.assertEqual(res_link.json['data']['item_title'], "Vaccines contain metal")
        self.assertEqual(res_link.json['data']['item_status'], "completed")

        # Try linking the same search again (Duplicate prevention check)
        res_dup = self.client.post(f'/api/cases/{case.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": s.id
        })
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn("already linked", res_dup.json['message'])
        print("[OK] Artifact linking, duplicate prevention, and metadata snapshots verified.")

    def test_05_cross_user_linking_protection(self):
        """Test that User A cannot link User B's search artifact to User A's case (returns 403)"""
        print("\n--- TEST 5: Cross-User Linking Validation ---")
        
        case_a = InvestigationCase(user_id=self.user_a.id, title="Case A Container")
        db.session.add(case_a)
        
        search_b = SearchHistory(user_id=self.user_b.id, query="User B Secret Search", search_status="completed")
        db.session.add(search_b)
        db.session.commit()

        # User A tries to link User B's search to User A's case
        res = self.client.post(f'/api/cases/{case_a.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": search_b.id
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.json['message'])
        print("[OK] Cross-user linking protection verified.")

    def test_06_archived_case_write_protection(self):
        """Test write locks on ARCHIVED cases (returns 400)"""
        print("\n--- TEST 6: Archived Case Write Protection ---")
        
        case = InvestigationCase(user_id=self.user_a.id, title="Archived Case Hub", status="ARCHIVED")
        db.session.add(case)
        
        search = SearchHistory(user_id=self.user_a.id, query="Vaccines hoax", search_status="completed")
        db.session.add(search)
        db.session.commit()

        # Try to update case description
        res_upd = self.client.put(f'/api/cases/{case.id}', headers=self.headers_a, json={
            "description": "Updated detail text."
        })
        self.assertEqual(res_upd.status_code, 400)
        self.assertIn("Cannot modify an archived case", res_upd.json['message'])

        # Try to link search item
        res_link = self.client.post(f'/api/cases/{case.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": search.id
        })
        self.assertEqual(res_link.status_code, 400)
        self.assertIn("Cannot modify an archived case", res_link.json['message'])
        print("[OK] Archived case write locks verified.")

    def test_07_activity_audit_logs(self):
        """Verify CaseActivity table log audit trail creation"""
        print("\n--- TEST 7: Case Activity Audit Logging ---")
        
        case = InvestigationCase(user_id=self.user_a.id, title="Audit Case")
        db.session.add(case)
        db.session.commit()

        # Generate activity log entries (CreateCase is logged in create_case automatically, but let's test manual actions)
        act1 = CaseActivity(case_id=case.id, action="CREATED_CASE")
        db.session.add(act1)
        
        search = SearchHistory(user_id=self.user_a.id, query="Audit Query")
        db.session.add(search)
        db.session.commit()
        
        # Link item (which triggers ATTACHED_ITEM)
        self.client.post(f'/api/cases/{case.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": search.id
        })

        # Fetch timeline from API
        res = self.client.get(f'/api/cases/{case.id}', headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        timeline = res.json['data']['timeline']
        
        # Ensure we have the audit timeline actions recorded
        actions = [t['action'] for t in timeline]
        self.assertIn("ATTACHED_ITEM", actions)
        print("[OK] CaseActivity audit logging verified.")

    def test_08_pagination_and_performance_benchmarks(self):
        """Test dashboard pagination parameters and performance benchmarking with 500 linked items"""
        print("\n--- TEST 8: Pagination and Load Performance ---")
        
        case = InvestigationCase(user_id=self.user_a.id, title="Huge Investigation Case")
        db.session.add(case)
        db.session.commit()

        # Link 500 mock search history query records to verify performance loading speeds
        items_batch = []
        for idx in range(500):
            item = CaseItem(
                case_id=case.id,
                item_type="search",
                item_id=idx + 1000,
                item_title=f"Mock Article Query {idx}",
                item_status="completed"
            )
            items_batch.append(item)
        db.session.bulk_save_objects(items_batch)
        db.session.commit()

        # Time the dashboard load speed
        start_time = time.perf_counter()
        res = self.client.get(f'/api/cases/{case.id}?page=1&page_size=25', headers=self.headers_a)
        end_time = time.perf_counter()
        
        self.assertEqual(res.status_code, 200)
        elapsed_ms = (end_time - start_time) * 1000
        
        # Verify pagination counts
        pag = res.json['data']['pagination']
        self.assertEqual(pag['total_items'], 500)
        self.assertEqual(pag['total_pages'], 20)
        self.assertEqual(len(res.json['data']['searches']), 25) # page size output limit

        print(f"[BENCHMARK] Paginated Case Dashboard with 500 items loaded in: {elapsed_ms:.2f} ms")
        self.assertLess(elapsed_ms, 100.0, "Dashboard load time must be <100ms")
        print("[OK] Pagination and dashboard performance benchmark validated.")

    def test_09_case_stats_and_non_destructive_deletes(self):
        """Test extended case stats calculations and verify deletes do not destroy linked artifacts"""
        print("\n--- TEST 9: Statistics Accuracy & Non-Destructive Purges ---")
        
        case = InvestigationCase(user_id=self.user_a.id, title="Compliance Case")
        db.session.add(case)
        db.session.commit()

        # Create SearchHistory query with misinformation
        s = SearchHistory(user_id=self.user_a.id, query="Climate change hoax", fact_check_result="MISINFORMATION DETECTED")
        db.session.add(s)
        db.session.commit()

        # Create Article first to satisfy foreign key constraints
        mock_art = Article(search_id=s.id, user_id=self.user_a.id, title="Mock Climate Article", url="https://mockclimate.com", content="Mock content here")
        db.session.add(mock_art)
        db.session.commit()

        # Create SentimentResult with high risk emotions linked to mock article
        art = SentimentResult(search_id=s.id, article_id=mock_art.id, risk_level="HIGH")
        db.session.add(art)
        db.session.commit()

        # Link search to Case
        self.client.post(f'/api/cases/{case.id}/items', headers=self.headers_a, json={
            "item_type": "search",
            "item_id": s.id
        })

        # Fetch stats
        res = self.client.get(f'/api/cases/{case.id}', headers=self.headers_a)
        stats = res.json['data']['statistics']
        self.assertEqual(stats['search_count'], 1)
        self.assertEqual(stats['misinformation_count'], 1)
        self.assertEqual(stats['high_risk_sentiment_count'], 1)

        # Delete the case (which purges case mapping)
        db.session.delete(case)
        db.session.commit()

        # Verify SearchHistory and SentimentResult still exist in db (Non-destructive check)
        self.assertIsNotNone(db.session.get(SearchHistory, s.id))
        self.assertIsNotNone(db.session.get(SentimentResult, art.id))
        print("[OK] Case statistics and non-destructive case deletions verified.")

if __name__ == "__main__":
    unittest.main()
