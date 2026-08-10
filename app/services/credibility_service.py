import re
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.extensions import db
from app.models.credibility import SourceCredibility, SourceCredibilityHistory
from app.models.article import Article
from app.models.fact_check import FactCheckResult
import tldextract

class CredibilityService:
    """Service to handle normalization, factor scoring, grade mapping, and history tracking for source credibility"""

    _normalization_cache = {}

    def normalize_domain(self, url):
        """
        Extracts and normalizes the registered domain from a URL:
        - Removes protocol (http, https)
        - Removes www.
        - Extracts registered domain using tldextract
        - Caches normalized domains in memory
        """
        if not url:
            return "unknown"
            
        if url in self._normalization_cache:
            return self._normalization_cache[url]

        normalized_url = url.strip()

        # Extract registered domain using tldextract
        try:
            ext = tldextract.extract(normalized_url)
            if ext.top_domain_under_public_suffix:
                domain = ext.top_domain_under_public_suffix.lower()
            else:
                # Fallback to standard urllib parse
                parsed = urllib.parse.urlparse(normalized_url)
                netloc = parsed.netloc.lower()
                if netloc.startswith('www.'):
                    netloc = netloc[4:]
                domain = netloc or "unknown"
        except Exception:
            domain = "unknown"

        self._normalization_cache[url] = domain
        return domain

    def resolve_redirects_and_normalize(self, url):
        """Resolves HTTP redirects (following headers) and normalizes the final destination URL domain"""
        if not url or not (url.startswith('http://') or url.startswith('https://')):
            return self.normalize_domain(url)
            
        try:
            # Perform a quick HEAD request to follow redirects
            res = requests.head(url, allow_redirects=True, timeout=5)
            final_url = res.url
        except Exception:
            final_url = url
            
        return self.normalize_domain(final_url)

    def get_letter_grade(self, score):
        """Maps numeric scores to academic letter grades"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def calculate_credibility(self, domain, articles=None, force=False):
        """
        Combines multiple weighted factors to produce a 0-100 credibility score.
        Uses cached db results if available within the last 24 hours (unless force=True).
        """
        if not domain or domain == "unknown":
            return {
                "domain": "unknown",
                "credibility_score": 0.0,
                "letter_grade": "F",
                "historical_misinformation_rate": 0.0,
                "fact_check_agreement_rate": 0.0,
                "source_consistency_score": 0.0,
                "domain_reputation_score": 0.0,
                "security_score": 0.0,
                "freshness_score": 0.0,
                "citation_score": 0.0,
                "analysis_count": 0
            }

        # 1. Check database cache (valid for 24 hours)
        cached_record = SourceCredibility.query.filter_by(domain=domain).first()
        one_day_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        if cached_record and not force:
            # Check age
            if cached_record.updated_at >= one_day_ago:
                current_app.logger.info(f"Source credibility cache hit for domain '{domain}'")
                return cached_record.to_dict()

        # 2. Gather factors
        
        # Factor B: Domain Reputation (Weight 20%)
        reputation_score = 70.0
        if domain.endswith('.gov') or domain.endswith('.edu'):
            reputation_score = 100.0
        elif domain in ['reuters.com', 'apnews.com', 'ap.org']:
            reputation_score = 95.0
        elif domain in ['nih.gov', 'cdc.gov', 'jamanetwork.com', 'nature.com', 'science.org']:
            reputation_score = 98.0
        elif domain in ['politifact.com', 'snopes.com', 'poynter.org', 'factcheck.org']:
            reputation_score = 95.0
        elif domain in ['nytimes.com', 'washingtonpost.com', 'bbc.co.uk', 'bbc.com', 'wsj.com']:
            reputation_score = 90.0
        elif domain in ['breitbart.com', 'infowars.com', 'naturalnews.com']:
            reputation_score = 30.0

        # Factor A: Historical Misinformation Rate (Weight 20%)
        # Query database for articles from this domain and check their fact audit verdicts.
        all_articles = Article.query.filter_by(source=domain).all()
        misinfo_count = 0
        total_audits = 0
        
        for art in all_articles:
            verdict = FactCheckResult.query.filter_by(article_id=art.id).first()
            if verdict:
                total_audits += 1
                if verdict.truth_rating == "MISINFORMATION DETECTED":
                    misinfo_count += 1
                    
        misinfo_rate = (misinfo_count / total_audits) if total_audits > 0 else 0.0
        agreement_rate = (1.0 - misinfo_rate) if total_audits > 0 else 1.0
        
        misinfo_score = 100.0 * (1.0 - misinfo_rate) if total_audits > 0 else reputation_score
        agreement_score = 100.0 * agreement_rate if total_audits > 0 else reputation_score

        # Factor C: Security Protocol (Weight 10%)
        security_score = 100.0
        if articles:
            test_url = articles[0].get('url', '')
            if test_url and test_url.startswith('http://'):
                security_score = 0.0
        else:
            if all_articles:
                if any(art.url and art.url.startswith('http://') for art in all_articles):
                    security_score = 0.0

        # Factor D: Freshness Score (Weight 10%)
        freshness_score = 100.0
        if articles:
            pub_dates = [a.get('published_at') for a in articles if a.get('published_at')]
            if pub_dates:
                valid_dates = []
                for d in pub_dates:
                    if isinstance(d, datetime):
                        valid_dates.append(d)
                    elif isinstance(d, str):
                        try:
                            valid_dates.append(datetime.fromisoformat(d.replace('Z', '+00:00')))
                        except Exception:
                            pass
                if valid_dates:
                    most_recent = max(valid_dates)
                    if most_recent.tzinfo is not None:
                        delta = datetime.now(timezone.utc) - most_recent
                    else:
                        delta = datetime.utcnow() - most_recent
                    days = delta.days
                    if days > 30:
                        freshness_score = max(0.0, 100.0 - (days - 30) * 0.5)

        # Factor E: Citation Quality (Weight 10%)
        citation_score = 70.0
        if articles:
            citation_counts = []
            for art in articles:
                content = art.get('content', '')
                matches = len(re.findall(r'(https?://[^\s]+|www\.[^\s]+|\[\d+\]|cite|source|according to|reported by)', content, re.IGNORECASE))
                if matches > 5:
                    citation_counts.append(100.0)
                elif matches > 2:
                    citation_counts.append(70.0)
                else:
                    citation_counts.append(40.0)
            if citation_counts:
                citation_score = sum(citation_counts) / len(citation_counts)

        # Factor F: Source Consistency (Weight 10%)
        consistency_score = 100.0
        
        # Calculate final combined score
        score = (
            (0.20 * misinfo_score) +
            (0.20 * agreement_score) +
            (0.20 * reputation_score) +
            (0.10 * security_score) +
            (0.10 * freshness_score) +
            (0.10 * citation_score) +
            (0.10 * consistency_score)
        )

        if domain.endswith('.gov') or domain.endswith('.edu'):
            score += 10.0
            
        score = max(0.0, min(100.0, score))
        letter_grade = self.get_letter_grade(score)

        # 3. Update Database (Insert or update rolling averages)
        if not cached_record:
            cached_record = SourceCredibility(
                domain=domain,
                credibility_score=score,
                letter_grade=letter_grade,
                historical_misinformation_rate=misinfo_rate,
                fact_check_agreement_rate=agreement_rate,
                source_consistency_score=consistency_score,
                domain_reputation_score=reputation_score,
                security_score=security_score,
                freshness_score=freshness_score,
                citation_score=citation_score,
                analysis_count=1
            )
            db.session.add(cached_record)
        else:
            cached_record.analysis_count += 1
            n = cached_record.analysis_count
            cached_record.credibility_score = round(((cached_record.credibility_score * (n - 1)) + score) / n, 2)
            cached_record.historical_misinformation_rate = round(((cached_record.historical_misinformation_rate * (n - 1)) + misinfo_rate) / n, 4)
            cached_record.fact_check_agreement_rate = round(((cached_record.fact_check_agreement_rate * (n - 1)) + agreement_rate) / n, 4)
            cached_record.source_consistency_score = round(((cached_record.source_consistency_score * (n - 1)) + consistency_score) / n, 2)
            cached_record.domain_reputation_score = round(((cached_record.domain_reputation_score * (n - 1)) + reputation_score) / n, 2)
            cached_record.security_score = round(((cached_record.security_score * (n - 1)) + security_score) / n, 2)
            cached_record.freshness_score = round(((cached_record.freshness_score * (n - 1)) + freshness_score) / n, 2)
            cached_record.citation_score = round(((cached_record.citation_score * (n - 1)) + citation_score) / n, 2)
            cached_record.letter_grade = self.get_letter_grade(cached_record.credibility_score)

        db.session.flush()

        # 4. Save history entry
        history_entry = SourceCredibilityHistory(
            source_credibility_id=cached_record.id,
            score=score,
            letter_grade=letter_grade,
            misinformation_rate=misinfo_rate,
            fact_check_agreement=agreement_rate
        )
        db.session.add(history_entry)
        db.session.commit()

        return cached_record.to_dict()
