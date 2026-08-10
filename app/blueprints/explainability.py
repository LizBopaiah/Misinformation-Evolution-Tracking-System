from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.report import ResearchReport
from app.models.explainability import ExplainabilityResult
from app.services.explainability_service import ExplainabilityService
from app.blueprints.api import make_success_response, make_error_response

explainability_bp = Blueprint('explainability', __name__, url_prefix='/api/explainability')

@explainability_bp.route('/search', methods=['POST'])
@jwt_required()
def generate_search_xai():
    """Generates or retrieves unified explainability snapshots for a search history query"""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    search_id = data.get("search_id")
    force_refresh = data.get("force_refresh", False)

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if not isinstance(search_id, int):
        return make_error_response("search_id must be an integer.", 400)

    search = db.session.get(SearchHistory, search_id)
    if not search or search.user_id != user_id:
        # Cross-user separation security requirement: return 404 instead of exposing resource existence
        return make_error_response("Search record not found.", 404)

    try:
        service = ExplainabilityService()
        result = service.generate_search_explainability(search_id, force_refresh=force_refresh)
        cached = result.pop("cached", False)
        return make_success_response(
            data=result,
            message="Search explainability generated successfully.",
            status_code=200
        )
    except Exception as e:
        current_app.logger.error(f"XAI generation failed: {str(e)}", exc_info=True)
        return make_error_response(f"Explainability generation failed: {str(e)}", 500)

@explainability_bp.route('/report', methods=['POST'])
@jwt_required()
def generate_report_xai():
    """Generates or retrieves explainability snapshots for a comparison report"""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    report_id = data.get("report_id")
    force_refresh = data.get("force_refresh", False)

    if not report_id:
        return make_error_response("report_id field is required.", 400)
    if not isinstance(report_id, int):
        return make_error_response("report_id must be an integer.", 400)

    report = db.session.get(ResearchReport, report_id)
    if not report or report.user_id != user_id:
        return make_error_response("Report record not found.", 404)

    try:
        service = ExplainabilityService()
        result = service.generate_report_explainability(report_id, force_refresh=force_refresh)
        cached = result.pop("cached", False)
        return make_success_response(
            data=result,
            message="Report explainability generated successfully.",
            status_code=200
        )
    except Exception as e:
        current_app.logger.error(f"Report XAI generation failed: {str(e)}", exc_info=True)
        return make_error_response(f"Report explainability generation failed: {str(e)}", 500)

@explainability_bp.route('/search/<int:search_id>', methods=['GET'])
@jwt_required()
def get_search_xai(search_id):
    """Retrieves the cached explainability snapshot for a search history query"""
    user_id = int(get_jwt_identity())
    search = db.session.get(SearchHistory, search_id)
    if not search or search.user_id != user_id:
        return make_error_response("Search record not found.", 404)

    cached = ExplainabilityResult.query.filter_by(search_id=search_id, explanation_type='search').first()
    if not cached:
        # Fallback generation on-the-fly if not already generated
        try:
            service = ExplainabilityService()
            result = service.generate_search_explainability(search_id)
            result.pop("cached", False)
            return make_success_response(
                data=result,
                message="Search explainability retrieved successfully.",
                status_code=200
            )
        except Exception as e:
            return make_error_response(f"Explainability query failed: {str(e)}", 500)

    return make_success_response(
        data=cached.to_dict(),
        message="Search explainability retrieved successfully.",
        status_code=200
    )

@explainability_bp.route('/report/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report_xai(report_id):
    """Retrieves the cached explainability snapshot for a comparison report"""
    user_id = int(get_jwt_identity())
    report = db.session.get(ResearchReport, report_id)
    if not report or report.user_id != user_id:
        return make_error_response("Report record not found.", 404)

    cached = ExplainabilityResult.query.filter_by(search_id=None, article_id=report_id, explanation_type='report').first()
    if not cached:
        try:
            service = ExplainabilityService()
            result = service.generate_report_explainability(report_id)
            result.pop("cached", False)
            return make_success_response(
                data=result,
                message="Report explainability retrieved successfully.",
                status_code=200
            )
        except Exception as e:
            return make_error_response(f"Report explainability query failed: {str(e)}", 500)

    return make_success_response(
        data=cached.to_dict(),
        message="Report explainability retrieved successfully.",
        status_code=200
    )

@explainability_bp.route('/<int:xai_id>', methods=['DELETE'])
@jwt_required()
def delete_xai(xai_id):
    """Removes an explainability snapshot manually"""
    user_id = int(get_jwt_identity())
    record = db.session.get(ExplainabilityResult, xai_id)
    if not record or record.user_id != user_id:
        return make_error_response("Explainability record not found.", 404)

    try:
        db.session.delete(record)
        db.session.commit()
        return make_success_response(
            message="Explainability record deleted successfully."
        )
    except Exception as e:
        db.session.rollback()
        return make_error_response(f"Failed to delete record: {str(e)}", 500)
