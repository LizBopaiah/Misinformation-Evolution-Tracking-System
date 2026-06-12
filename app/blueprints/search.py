import time
from functools import wraps
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.article import Article
from app.services.search_service import SearchService
from app.services.scraping_service import ScrapingService
from app.services.summarization_service import SummarizationService
from app.services.fact_checking_service import FactCheckingService
from app.blueprints.api import make_success_response, make_error_response

search_bp = Blueprint('search', __name__, url_prefix='/api')

# In-memory store for rate limiting: key -> list of timestamps
_rate_limit_store = {}

def rate_limit(limit=5, period=60):
    """
    Decorator to rate limit endpoints.
    Defaults to 5 requests per 60 seconds.
    Identifies requests by user ID (if authenticated) or IP address.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
                key = f"user_{user_id}" if user_id else f"ip_{request.remote_addr}"
            except Exception:
                key = f"ip_{request.remote_addr}"

            now = time.time()
            if key not in _rate_limit_store:
                _rate_limit_store[key] = []
            
            _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < period]
            
            if len(_rate_limit_store[key]) >= limit:
                current_app.logger.warning(
                    f"Rate limit exceeded for {key} on {request.path}. "
                    f"Count: {len(_rate_limit_store[key]) + 1}/{limit} in {period}s."
                )
                return make_error_response(
                    message="Too many requests. Please try again later.",
                    status_code=429
                )
            
            _rate_limit_store[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

@search_bp.route('/search', methods=['POST'])
@jwt_required()
@rate_limit(limit=5, period=60)
def run_search():
    """
    Executes search query, scrapes articles, deduplicates, summarizes,
    fact-checks, and stores history and article records.
    """
    user_id = int(get_jwt_identity())
    
    # 1. Input Validation
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    try:
        data = request.get_json()
    except Exception:
        return make_error_response("Malformed JSON payload.", 400)
        
    if data is None or not isinstance(data, dict):
        return make_error_response("Invalid request payload structure.", 400)
        
    query = data.get('query', '')
    if query is None or not isinstance(query, str):
        return make_error_response("Query must be a string.", 400)
        
    query = query.strip()
    if not query:
        return make_error_response("Query field is required.", 400)
        
    if len(query) > 200:
        return make_error_response("Query must not exceed 200 characters.", 400)
        
    # Check if a completed search history for this exact query already exists for this user in the last 24 hours
    from datetime import datetime, timedelta, timezone
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    
    # We query using timezone-aware created_at if possible, or naive comparison depending on database values
    existing_search = db.session.query(SearchHistory).filter(
        SearchHistory.user_id == user_id,
        db.func.lower(SearchHistory.query) == query.lower(),
        SearchHistory.status == 'completed',
        SearchHistory.created_at >= one_day_ago
    ).order_by(SearchHistory.created_at.desc()).first()
    
    if existing_search:
        current_app.logger.info(f"Complete search history cache hit for query '{query}'")
        associated_articles = Article.query.filter_by(search_id=existing_search.id).all()
        return make_success_response(
            data={
                "id": existing_search.id,
                "query": existing_search.query,
                "summary": existing_search.summary,
                "fact_check_result": existing_search.fact_check_result,
                "articles_collected": existing_search.articles_collected,
                "processing_time": existing_search.processing_time,
                "search_status": existing_search.search_status,
                "created_at": existing_search.created_at.isoformat() if existing_search.created_at else None,
                "articles": [a.to_dict() for a in associated_articles]
            },
            message="Search analysis retrieved from cache."
        )

    start_time = time.time()

    
    # 1. Create a pending search history log
    search_log = SearchHistory(
        user_id=user_id,
        query=query,
        search_type='general',
        status='pending',
        search_status='pending',
        articles_collected=0
    )
    db.session.add(search_log)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_error_response(f"Database error initializing search log: {str(e)}", 500)
        
    search_id = search_log.id
    current_app.logger.info(f"Initialized SearchHistory row ID {search_id} for query '{query}'")

    try:
        # 2. Run Google Custom Search
        search_svc = SearchService()
        search_results = search_svc.execute_search(query, num_results=10)
        
        # 3. Scrape results (limit to top 10 most relevant from execution)
        scraping_svc = ScrapingService()
        scraped_raw = []
        for result in search_results:
            try:
                scraped_art = scraping_svc.scrape_url(result['link'])
                if scraped_art and scraped_art.get('content'):
                    # Retain original snippet and title if scrape is poor
                    if not scraped_art.get('title') or scraped_art['title'] == f"Article from {scraped_art['source']}":
                        scraped_art['title'] = result['title']
                    scraped_raw.append(scraped_art)
            except Exception as e:
                current_app.logger.warning(f"Failed to scrape url {result['link']}: {str(e)}")

        # 4. Deduplicate articles using TF-IDF similarity (> 95% threshold)
        deduplicated = scraping_svc.deduplicate_articles(scraped_raw, similarity_threshold=0.95)
        
        # 5. Limit final collection to top 10
        final_articles = deduplicated[:10]
        
        # 6. Save articles to Database (preventing duplicates using unique URL)
        articles_saved = []
        for art in final_articles:
            # Check unique URL
            existing_article = Article.query.filter_by(url=art['url']).first()
            if existing_article:
                # Update attributes to associate with latest search and update content
                existing_article.search_id = search_id
                existing_article.user_id = user_id
                existing_article.title = art['title']
                existing_article.content = art['content']
                existing_article.source = art['source']
                existing_article.content_hash = art['content_hash']
                if art['published_at']:
                    existing_article.published_at = art['published_at']
                articles_saved.append(existing_article)
            else:
                new_art = Article(
                    search_id=search_id,
                    user_id=user_id,
                    url=art['url'],
                    title=art['title'],
                    content=art['content'],
                    source=art['source'],
                    published_at=art['published_at'],
                    content_hash=art['content_hash']
                )
                db.session.add(new_art)
                articles_saved.append(new_art)

        # Commit articles to make sure ids are generated
        db.session.commit()

        # 7. Generate narrative summary
        summarization_svc = SummarizationService()
        summary = summarization_svc.generate_summary(final_articles)
        
        # 8. Fact checking verdict (hybrid model + Gemini)
        fact_checking_svc = FactCheckingService()
        verdict = fact_checking_svc.verify_claim(query, final_articles)
        
        # 9. Compute execution stats and save
        processing_time = round(time.time() - start_time, 2)
        
        search_log.summary = summary
        search_log.fact_check_result = verdict
        search_log.articles_collected = len(articles_saved)
        search_log.processing_time = processing_time
        search_log.status = 'completed'
        search_log.search_status = 'completed'
        
        db.session.commit()
        
        return make_success_response(
            data={
                "id": search_log.id,
                "query": search_log.query,
                "summary": search_log.summary,
                "fact_check_result": search_log.fact_check_result,
                "articles_collected": search_log.articles_collected,
                "processing_time": search_log.processing_time,
                "search_status": search_log.search_status,
                "created_at": search_log.created_at.isoformat() if search_log.created_at else None,
                "articles": [a.to_dict() for a in articles_saved]
            },
            message="Search analysis completed successfully."
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error executing search query flow: {str(e)}", exc_info=True)
        # Update search status to failed
        try:
            search_log.status = 'failed'
            search_log.search_status = 'failed'
            db.session.commit()
        except Exception:
            db.session.rollback()
        return make_error_response(f"An error occurred during query analysis: {str(e)}", 500)

@search_bp.route('/search/<int:search_id>', methods=['GET'])
@jwt_required()
def get_search_details(search_id):
    """Retrieves full details of a past search history query, including associated articles"""
    user_id = int(get_jwt_identity())
    search = db.session.get(SearchHistory, search_id)
    
    if not search:
        return make_error_response("Search record not found.", 404)
        
    if search.user_id != user_id:
        return make_error_response("You do not have permission to view this search history.", 403)
        
    # Get associated articles
    articles = Article.query.filter_by(search_id=search_id).all()
    
    return make_success_response(
        data={
            "id": search.id,
            "query": search.query,
            "summary": search.summary,
            "fact_check_result": search.fact_check_result,
            "articles_collected": search.articles_collected,
            "processing_time": search.processing_time,
            "search_status": search.search_status,
            "created_at": search.created_at.isoformat() if search.created_at else None,
            "articles": [a.to_dict() for a in articles]
        },
        message="Search details retrieved successfully."
    )

@search_bp.route('/articles/<int:article_id>', methods=['GET'])
@jwt_required()
def get_article_details(article_id):
    """Retrieves full body content and metadata for a specific article"""
    user_id = int(get_jwt_identity())
    article = Article.query.get(article_id)
    
    if not article:
        return make_error_response("Article not found.", 404)
        
    if article.user_id != user_id:
        return make_error_response("You do not have permission to view this article.", 403)
        
    return make_success_response(
        data=article.to_dict(),
        message="Article details retrieved successfully."
    )

@search_bp.route('/search-history', methods=['GET'])
@jwt_required()
def get_search_history_endpoint():
    """Retrieves user's search history logs sorted chronologically"""
    user_id = int(get_jwt_identity())
    searches = db.session.query(SearchHistory).filter_by(user_id=user_id).order_by(SearchHistory.created_at.desc()).all()
    
    return make_success_response(
        data=[
            {
                "id": s.id,
                "query": s.query,
                "summary": s.summary,
                "fact_check_result": s.fact_check_result,
                "articles_collected": s.articles_collected,
                "processing_time": s.processing_time,
                "search_status": s.search_status,
                "created_at": s.created_at.isoformat() if s.created_at else None
            } for s in searches
        ],
        message="Search history retrieved successfully."
    )

@search_bp.route('/search/reset-limiter', methods=['POST'])
def reset_limiter():
    """Reset rate limiter store for testing (only in debug mode)"""
    if not current_app.debug:
        return make_error_response("Not allowed.", 403)
    _rate_limit_store.clear()
    return make_success_response(message="Rate limiter reset successfully.")
