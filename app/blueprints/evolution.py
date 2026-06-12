from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.evolution import EvolutionResult
from app.services.evolution_service import EvolutionService
from app.blueprints.api import make_success_response, make_error_response

evolution_bp = Blueprint('evolution', __name__, url_prefix='/api/evolution')

@evolution_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_evolution():
    """
    Triggers narrative evolution, similarity indexing, and clustering analysis
    for all articles associated with a completed search history record.
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
        return make_error_response("Evolution analysis requires a completed search record.", 400)

    # 3. Retrieve associated articles
    articles = db.session.query(Article).filter_by(search_id=search_id).all()
    if not articles:
        return make_error_response("No articles found associated with this search history.", 400)

    # 4. Check Cache
    existing_res = db.session.query(EvolutionResult).filter_by(search_id=search_id).first()
    if existing_res:
        current_app.logger.info(f"Evolution cache hit for search ID {search_id}")
        data_response = existing_res.to_dict()
        data_response["cached"] = True
        return make_success_response(
            data=data_response,
            message="Narrative evolution retrieved from cache."
        )

    # 5. Run analysis pipeline
    try:
        evolution_svc = EvolutionService()
        result = evolution_svc.analyze_evolution(articles)
    except Exception as e:
        current_app.logger.error(f"Evolution Service analysis failed: {str(e)}", exc_info=True)
        return make_error_response(f"Evolution analysis service error: {str(e)}", 500)

    # 6. Store result in database
    res = EvolutionResult(
        search_id=search_id,
        user_id=user_id,
        baseline_article_id=result["baseline_article_id"],
        narrative_drift_score=result["narrative_drift_score"],
        total_variants_detected=result["total_variants_detected"],
        dominant_narrative=result["dominant_narrative"],
        evolution_summary=result["evolution_summary"]
    )
    res.mutation_points = result["mutation_points"]
    res.timeline = result["timeline"]

    db.session.add(res)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to commit evolution analysis result: {str(e)}")
        return make_error_response("Failed to persist evolution results to database.", 500)

    # 7. Format success response
    data_response = res.to_dict()
    data_response["cached"] = False
    return make_success_response(
        data=data_response,
        message="Narrative evolution analysis executed successfully."
    )


@evolution_bp.route('/<int:search_id>', methods=['GET'])
@jwt_required()
def get_evolution(search_id):
    """
    Retrieves stored evolution analysis results for a given search query.
    Returns 404 if analysis does not exist.
    """
    user_id = int(get_jwt_identity())

    # 1. Ownership validation
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search history not found or access denied.", 404)

    # 2. Query stored evolution results
    res = db.session.query(EvolutionResult).filter_by(search_id=search_id).first()
    if not res:
        return make_error_response("Evolution analysis results have not been generated for this search yet.", 404)

    data_response = res.to_dict()
    data_response["cached"] = True
    return make_success_response(
        data=data_response,
        message="Narrative evolution analysis retrieved successfully."
    )
