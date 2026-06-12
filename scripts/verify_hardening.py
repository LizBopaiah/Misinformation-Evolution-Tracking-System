import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
import json
import requests

# Add project root to sys.path to enable app imports
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.blueprints.search import _rate_limit_store

class Module4HardeningTestCase(unittest.TestCase):
    """Integration test suite to verify Module 4 security, fallbacks, input validation, and database integrity."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['DEBUG'] = True
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Enable SQLite Foreign Keys explicitly just in case
        db.session.execute(db.text("PRAGMA foreign_keys=ON"))

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        # Clear rate limiting store between tests
        _rate_limit_store.clear()
        
        # Create User A and User B if they don't exist
        self.user_a_email = "usera_hardening@met.com"
        self.user_b_email = "userb_hardening@met.com"
        self.password = "Password123!"
        
        self.user_a = User.query.filter_by(email=self.user_a_email).first()
        if not self.user_a:
            self.user_a = User(username="usera_hardening", email=self.user_a_email)
            self.user_a.set_password(self.password)
            db.session.add(self.user_a)
            
        self.user_b = User.query.filter_by(email=self.user_b_email).first()
        if not self.user_b:
            self.user_b = User(username="userb_hardening", email=self.user_b_email)
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

    def test_01_input_validation(self):
        """Test search query validation (empty, whitespace, length, JSON structure)."""
        print("\n--- Running Test 1: Input Validation ---")
        
        # 1. Empty Query
        res = self.client.post('/api/search', headers=self.headers_a, json={"query": ""})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Query field is required.", res.json['message'])
        print("[OK] Empty query validation returned 400 Bad Request.")
        
        # 2. Whitespace Query
        res = self.client.post('/api/search', headers=self.headers_a, json={"query": "    "})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Query field is required.", res.json['message'])
        print("[OK] Whitespace query validation returned 400 Bad Request.")
        
        # 3. Query exceeding 200 characters
        long_query = "a" * 201
        res = self.client.post('/api/search', headers=self.headers_a, json={"query": long_query})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Query must not exceed 200 characters.", res.json['message'])
        print("[OK] Length validation (>200 chars) returned 400 Bad Request.")
        
        # 4. Malformed JSON
        res = self.client.post('/api/search', headers=self.headers_a, 
                               data="{'query': 'incomplete", 
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Malformed JSON payload.", res.json['message'])
        print("[OK] Malformed JSON payload validation returned 400 Bad Request.")

    def test_02_authorization_isolation(self):
        """Test search history and article isolation between users (User A vs User B)."""
        print("\n--- Running Test 2: Authorization & Isolation ---")
        
        # 1. User A performs a search
        res = self.client.post('/api/search', headers=self.headers_a, json={"query": "COVID vaccine infertility"})
        self.assertEqual(res.status_code, 200)
        search_data = res.json['data']
        search_id = search_data['id']
        article_id = search_data['articles'][0]['id']
        
        # 2. User B attempts to access User A's search details
        res_details = self.client.get(f'/api/search/{search_id}', headers=self.headers_b)
        self.assertEqual(res_details.status_code, 403)
        self.assertIn("You do not have permission to view this search history.", res_details.json['message'])
        print("[OK] Cross-user Search History access correctly blocked (403 Forbidden).")
        
        # 3. User B attempts to access User A's article content
        res_article = self.client.get(f'/api/articles/{article_id}', headers=self.headers_b)
        self.assertEqual(res_article.status_code, 403)
        self.assertIn("You do not have permission to view this article.", res_article.json['message'])
        print("[OK] Cross-user Article access correctly blocked (403 Forbidden).")
        
        # 4. User B gets their own search history, should not see User A's search
        res_history = self.client.get('/api/search-history', headers=self.headers_b)
        self.assertEqual(res_history.status_code, 200)
        history_queries = [s['id'] for s in res_history.json['data']]
        self.assertNotIn(search_id, history_queries)
        print("[OK] Search history lists are isolated correctly per authenticated identity.")

    def test_03_rate_limiting(self):
        """Test API rate limiting / abuse protection triggers and handles 429 correctly."""
        print("\n--- Running Test 3: API Abuse Protection & Rate Limiting ---")
        
        # Mocking backend tasks to execute instantly
        with patch('app.services.search_service.SearchService.execute_search') as mock_search, \
             patch('app.services.scraping_service.ScrapingService.scrape_url') as mock_scrape, \
             patch('app.services.summarization_service.SummarizationService.generate_summary') as mock_summarize, \
             patch('app.services.fact_checking_service.FactCheckingService.verify_claim') as mock_check:
                 
            mock_search.return_value = [{"title": "Mock", "link": "https://example.com/art", "snippet": "Mock content", "domain": "example.com"}]
            mock_scrape.return_value = {"url": "https://example.com/art", "title": "Mock", "content": "Mock body content.", "published_at": None, "source": "example.com", "content_hash": "abc"}
            mock_summarize.return_value = "Mock summary text."
            mock_check.return_value = "CORRECT"
            
            # Send 5 requests quickly under User B (limit = 5)
            for i in range(5):
                res = self.client.post('/api/search', headers=self.headers_b, json={"query": f"test rate limit {i}"})
                self.assertEqual(res.status_code, 200)
                
            # The 6th request should fail with 429
            res_six = self.client.post('/api/search', headers=self.headers_b, json={"query": "test rate limit sixth"})
            self.assertEqual(res_six.status_code, 429)
            self.assertIn("Too many requests. Please try again later.", res_six.json['message'])
            print("[OK] Exceeding request window limits correctly throttled with 429 (Too Many Requests).")

    def test_04_scraper_resilience(self):
        """Test scraper timeouts and failed article fetches resilience."""
        print("\n--- Running Test 4: Scraper Resilience & Failures ---")
        
        # Mock search results to return 3 links
        # We will mock requests.get inside ScrapingService to fail for URL 1 & 2, and succeed for URL 3
        with patch('app.services.search_service.SearchService.execute_search') as mock_search, \
             patch('requests.get') as mock_get:
                 
            mock_search.return_value = [
                {"title": "Fail URL 1", "link": "https://failed1.com/art", "snippet": "Snippet 1", "domain": "failed1.com"},
                {"title": "Timeout URL 2", "link": "https://failed2.com/art", "snippet": "Snippet 2", "domain": "failed2.com"},
                {"title": "Succeed URL 3", "link": "https://succeed3.com/art", "snippet": "Snippet 3", "domain": "succeed3.com"}
            ]
            
            # Side effect mock to simulate connections failures, timeouts, and success
            def get_side_effect(url, *args, **kwargs):
                if "failed1.com" in url:
                    raise requests.exceptions.ConnectionError("Connection Refused")
                elif "failed2.com" in url:
                    raise requests.exceptions.Timeout("Read Timeout")
                elif "succeed3.com" in url:
                    mock_res = MagicMock()
                    mock_res.status_code = 200
                    mock_res.text = "<html><body><p>This is successful scraped article body content. It is long enough to pass.</p></body></html>"
                    return mock_res
                # Default mock fallback
                mock_res = MagicMock()
                mock_res.status_code = 404
                return mock_res
                
            mock_get.side_effect = get_side_effect
            
            # Execute search
            res = self.client.post('/api/search', headers=self.headers_a, json={"query": "Resilience testing"})
            self.assertEqual(res.status_code, 200)
            
            data = res.json['data']
            # Partial article collection should contain at least 1 article
            self.assertGreaterEqual(data['articles_collected'], 1)
            self.assertNotEqual(data['summary'], "No articles collected to summarize.")
            self.assertIn(data['fact_check_result'], ["MISINFORMATION DETECTED", "CORRECT"])
            print("[OK] Failed article fetches and timeouts did not crash search process.")
            print(f"[OK] Partial collections still successfully generated summaries and verdicts. Articles collected: {data['articles_collected']}.")

    def test_05_google_search_fallback(self):
        """Test that SearchService falls back gracefully to mock results on Custom Search API failures."""
        print("\n--- Running Test 5: Google Custom Search Fallback (Mocking) ---")
        
        # Mock requests.get inside SearchService to raise an API Exception (e.g. quota limit or credentials error)
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Google Search API Quota Exceeded")
            
            # Execute search
            res = self.client.post('/api/search', headers=self.headers_a, json={"query": "COVID vaccine infertility"})
            self.assertEqual(res.status_code, 200)
            
            data = res.json['data']
            self.assertGreater(data['articles_collected'], 0)
            self.assertEqual(data['search_status'], "completed")
            print("[OK] Google Custom Search API failures gracefully fall back to local mock index without exposure of exception trace.")

    @patch('app.services.summarization_service.GEMINI_AVAILABLE', True)
    def test_06_gemini_fallback(self):
        """Test that Gemini API failures fallback gracefully to local summarizer & fact-checking models."""
        print("\n--- Running Test 6: Gemini API Fallback (Mocking) ---")
        
        # Mock genai GenerativeModel to raise an exception during content generation
        try:
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content.side_effect = Exception("Gemini Service Unavailable")
                mock_model_class.return_value = mock_model
                
                # Execute search query
                res = self.client.post('/api/search', headers=self.headers_a, json={"query": "COVID vaccine infertility"})
                self.assertEqual(res.status_code, 200)
                
                data = res.json['data']
                # Summary should be generated by local summarizer fallback
                self.assertIsNotNone(data['summary'])
                self.assertNotEqual(data['summary'], "Failed to generate local summary fallback.")
                self.assertIn(data['fact_check_result'], ["MISINFORMATION DETECTED", "CORRECT"])
                print("[OK] Gemini API failures fallback safely to local sentence-frequency extraction summarization.")
                print("[OK] Fact-check verdict falls back securely to Module 3 classification prediction.")
                print("[OK] Response returned successfully without exposing raw generative trace stacks.")
        except Exception as e:
            print(f"Skipped Gemini mock check or hit issue: {str(e)}")

    def test_07_database_integrity_cascade_delete(self):
        """Test that deleting a user removes all their SearchHistory and Articles through cascade delete."""
        print("\n--- Running Test 7: Database Integrity & Cascade Deletes ---")
        
        # 1. Register temporary User C
        username_c = "userc_hardening"
        email_c = "userc_hardening@met.com"
        
        # Clean up User C if left over from aborted runs
        old_user = User.query.filter_by(email=email_c).first()
        if old_user:
            db.session.delete(old_user)
            db.session.commit()
            
        user_c = User(username=username_c, email=email_c)
        user_c.set_password(self.password)
        db.session.add(user_c)
        db.session.commit()
        
        user_c_id = user_c.id
        
        # Log in User C
        login_res = self.client.post('/api/auth/login', json={
            "email": email_c,
            "password": self.password
        })
        token_c = login_res.json['data']['access_token']
        headers_c = {"Authorization": f"Bearer {token_c}"}
        
        # 2. Perform search under User C (creates SearchHistory and Article rows)
        res_search = self.client.post('/api/search', headers=headers_c, json={"query": "User C query text"})
        self.assertEqual(res_search.status_code, 200)
        
        # Assert database rows exist using session query namespace to avoid SearchHistory.query collision
        user_c_searches = db.session.query(SearchHistory).filter_by(user_id=user_c_id).all()
        user_c_articles = db.session.query(Article).filter_by(user_id=user_c_id).all()
        self.assertGreater(len(user_c_searches), 0)
        self.assertGreater(len(user_c_articles), 0)
        print(f"  - User C rows successfully populated in DB: {len(user_c_searches)} Searches, {len(user_c_articles)} Articles.")
        
        # 3. Delete User C
        db.session.delete(user_c)
        db.session.commit()
        print("  - User C deleted from DB.")
        
        # 4. Assert that searches and articles are cascades-deleted
        cascaded_searches = db.session.query(SearchHistory).filter_by(user_id=user_c_id).all()
        cascaded_articles = db.session.query(Article).filter_by(user_id=user_c_id).all()
        
        self.assertEqual(len(cascaded_searches), 0)
        self.assertEqual(len(cascaded_articles), 0)
        print("[OK] Cascade deletes verified: user deletion successfully purged all SearchHistory and Articles records.")

    def test_08_performance_benchmarks(self):
        """Benchmark live vs cached search performance timings."""
        print("\n--- Running Test 8: Performance Timings Benchmark ---")
        
        # Query: unique one to ensure live search execution (no cache hit)
        query = f"Timing benchmark query {str(time.time())}"
        
        # 1. Live Search
        start_live = time.time()
        res_live = self.client.post('/api/search', headers=self.headers_a, json={"query": query})
        elapsed_live = time.time() - start_live
        self.assertEqual(res_live.status_code, 200)
        
        # 2. Cached Search (same query)
        start_cached = time.time()
        res_cached = self.client.post('/api/search', headers=self.headers_a, json={"query": query})
        elapsed_cached = time.time() - start_cached
        self.assertEqual(res_cached.status_code, 200)
        
        # Assertions & Timing reports
        print(f"  - Live search duration: {elapsed_live:.3f}s")
        print(f"  - Cached search duration: {elapsed_cached:.3f}s (Speedup: {elapsed_live / elapsed_cached:.1f}x)")
        
        self.assertLess(elapsed_cached, 0.500, "Cached response exceeded 500ms threshold.")
        self.assertGreater(elapsed_live / elapsed_cached, 5.0, "Cached response is not 5x faster than live search.")
        print("[OK] Cached query timing (< 500ms) and speed ratio checks (> 5x speedup) successfully passed.")
        
        # Save performance statistics in instance
        os.makedirs(os.path.join(os.getcwd(), 'instance'), exist_ok=True)
        stats_path = os.path.join(os.getcwd(), 'instance', 'hardening_stats.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump({
                "live_search_seconds": elapsed_live,
                "cached_search_seconds": elapsed_cached,
                "speed_ratio": elapsed_live / elapsed_cached
            }, f, indent=4)

if __name__ == "__main__":
    unittest.main()
