from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.sentiment import SentimentResult
from app.services.sentiment_service import SentimentService
from app.blueprints.api import make_success_response, make_error_response

sentiment_bp = Blueprint('sentiment', __name__, url_prefix='/api/sentiment')

@sentiment_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_sentiment():
    """
    Triggers sentiment and emotional manipulation analysis for all articles
    associated with a completed search history record.
    Supports caching and upserts (duplicate prevention).
    """
    user_id = int(get_jwt_identity())
    
    # 1. Parse and validate JSON input
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    try:
        data = request.get_json()
    except Exception:
        return make_error_response("Malformed JSON payload.", 400)
        
    if data is None or not isinstance(data, dict):
        return make_error_response("Invalid request payload structure.", 400)
        
    search_id = data.get('search_id')
    if search_id is None:
        return make_error_response("search_id field is required.", 400)
        
    try:
        search_id = int(search_id)
    except (ValueError, TypeError):
        return make_error_response("search_id must be an integer.", 400)
        
    # 2. Check search history ownership
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search history not found or access denied.", 404)
        
    if search.status != 'completed':
        return make_error_response("Sentiment analysis requires a completed search record.", 400)
        
    # 3. Retrieve associated articles
    articles = db.session.query(Article).filter_by(search_id=search_id).all()
    if not articles:
        return make_error_response("No articles found associated with this search history.", 400)
        
    # 4. Check Cache
    article_ids = {a.id for a in articles}
    existing_results = db.session.query(SentimentResult).filter_by(search_id=search_id).all()
    sent_article_ids = {r.article_id for r in existing_results}
    
    if search.sentiment_analyzed_at is not None and article_ids == sent_article_ids:
        # Cache hit
        current_app.logger.info(f"Sentiment cache hit for search ID {search_id}")
        
        # Build articles response list using cached rows
        articles_response = []
        for art in articles:
            res = next(r for r in existing_results if r.article_id == art.id)
            articles_response.append({
                "article_id": art.id,
                "title": art.title,
                "dominant_emotion": res.dominant_emotion,
                "confidence": res.confidence,
                "emotion_distribution": res.emotion_distribution,
                "risk_level": res.risk_level,
                "model_version": res.model_version
            })
            
        return make_success_response(
            data={
                "cached": True,
                "search_id": search_id,
                "overall_emotion": search.overall_emotion,
                "overall_risk_level": search.overall_risk_level,
                "emotion_distribution": search.aggregated_emotion_distribution,
                "sentiment_analyzed_at": search.sentiment_analyzed_at.isoformat() if search.sentiment_analyzed_at else None,
                "articles": articles_response
            },
            message="Sentiment analysis retrieved from cache."
        )
        
    # 5. Model Loading (Graceful 503 Fallback if files missing)
    try:
        sentiment_svc = SentimentService()
        sentiment_svc._load_model()
    except FileNotFoundError as e:
        current_app.logger.error(f"Sentiment Service error: {str(e)}")
        return make_error_response("Sentiment analysis service is temporarily offline due to missing model artifacts.", 503)
        
    # 6. Run Model Inference (Batch vectorized)
    texts = [art.content for art in articles]
    analysis_outputs = sentiment_svc.analyze_texts_batch(texts)
    
    # 7. Upsert results into database to prevent duplication
    results_map = {r.article_id: r for r in existing_results}
    distributions = []
    
    for art, out in zip(articles, analysis_outputs):
        res = results_map.get(art.id)
        if not res:
            res = SentimentResult(article_id=art.id, search_id=search_id)
            db.session.add(res)
            
        res.dominant_emotion = out["dominant_emotion"]
        res.confidence = out["confidence"]
        res.emotion_distribution = out["distribution"]
        res.risk_level = out["risk_level"]
        res.model_version = out["model_version"]
        
        distributions.append(out["distribution"])
        
    # 8. Calculate aggregate metrics
    aggregate = sentiment_svc.aggregate_results(distributions)
    
    # Update search aggregate cache
    search.overall_emotion = aggregate["overall_emotion"]
    search.overall_risk_level = aggregate["overall_risk_level"]
    search.aggregated_emotion_distribution = aggregate["emotion_distribution"]
    search.sentiment_analyzed_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to commit sentiment results: {str(e)}")
        return make_error_response("Failed to persist sentiment analysis to the database.", 500)
        
    # 9. Format response
    articles_response = []
    for art in articles:
        res = db.session.query(SentimentResult).filter_by(article_id=art.id).first()
        articles_response.append({
            "article_id": art.id,
            "title": art.title,
            "dominant_emotion": res.dominant_emotion,
            "confidence": res.confidence,
            "emotion_distribution": res.emotion_distribution,
            "risk_level": res.risk_level,
            "model_version": res.model_version
        })
        
    return make_success_response(
        data={
            "cached": False,
            "search_id": search_id,
            "overall_emotion": search.overall_emotion,
            "overall_risk_level": search.overall_risk_level,
            "emotion_distribution": search.aggregated_emotion_distribution,
            "sentiment_analyzed_at": search.sentiment_analyzed_at.isoformat() if search.sentiment_analyzed_at else None,
            "articles": articles_response
        },
        message="Sentiment analysis executed successfully."
    )

@sentiment_bp.route('/<int:search_id>', methods=['GET'])
@jwt_required()
def get_sentiment(search_id):
    """
    Retrieves stored sentiment results and aggregate analysis for a given search query.
    Returns 404 if analysis does not exist.
    """
    user_id = int(get_jwt_identity())
    
    # 1. Ownership validation
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search history not found or access denied.", 404)
        
    # 2. Check if analysis generated
    if search.sentiment_analyzed_at is None:
        return make_error_response("Sentiment analysis results have not been generated for this search yet.", 404)
        
    articles = db.session.query(Article).filter_by(search_id=search_id).all()
    existing_results = db.session.query(SentimentResult).filter_by(search_id=search_id).all()
    
    if len(existing_results) != len(articles) or not articles:
        # DB integrity issues or analysis not completed
        return make_error_response("Sentiment analysis results are partial or missing.", 404)
        
    # 3. Format response
    articles_response = []
    for art in articles:
        res = next(r for r in existing_results if r.article_id == art.id)
        articles_response.append({
            "article_id": art.id,
            "title": art.title,
            "dominant_emotion": res.dominant_emotion,
            "confidence": res.confidence,
            "emotion_distribution": res.emotion_distribution,
            "risk_level": res.risk_level,
            "model_version": res.model_version
        })
        
    return make_success_response(
        data={
            "cached": True,
            "search_id": search_id,
            "overall_emotion": search.overall_emotion,
            "overall_risk_level": search.overall_risk_level,
            "emotion_distribution": search.aggregated_emotion_distribution,
            "sentiment_analyzed_at": search.sentiment_analyzed_at.isoformat() if search.sentiment_analyzed_at else None,
            "articles": articles_response
        },
        message="Sentiment analysis retrieved successfully."
    )
