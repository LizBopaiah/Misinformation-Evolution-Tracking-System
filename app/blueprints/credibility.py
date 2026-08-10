from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from app.services.credibility_service import CredibilityService
from app.blueprints.api import make_success_response, make_error_response
from app.models.credibility import SourceCredibility

credibility_bp = Blueprint('credibility', __name__, url_prefix='/api')

@credibility_bp.route('/credibility/<string:domain>', methods=['GET'])
@jwt_required()
def get_credibility(domain):
    """
    Retrieves the current source credibility rating, history list, 
    and metric breakdowns for a normalized domain.
    """
    if not domain or '/' in domain or '\\' in domain:
        return make_error_response("Invalid domain string.", 400)

    svc = CredibilityService()
    normalized_domain = svc.normalize_domain(domain)
    
    try:
        data = svc.calculate_credibility(normalized_domain)
        # Fetch history trends
        record = SourceCredibility.query.filter_by(domain=normalized_domain).first()
        history_list = []
        if record:
            history_list = [h.to_dict() for h in record.history]
        data['history'] = history_list
        return make_success_response(data=data, message="Source credibility retrieved successfully.")
    except Exception as e:
        current_app.logger.error(f"Error checking credibility for {domain}: {str(e)}")
        return make_error_response(f"Server error: {str(e)}", 500)

@credibility_bp.route('/credibility/recalculate', methods=['POST'])
@jwt_required()
def force_recalculate():
    """Forces recalculation of credibility indicators for a specified domain"""
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)

    data = request.get_json()
    domain = data.get('domain', '').strip()
    if not domain:
        return make_error_response("Domain field is required.", 400)

    svc = CredibilityService()
    normalized = svc.normalize_domain(domain)
    
    try:
        result = svc.calculate_credibility(normalized, force=True)
        return make_success_response(data=result, message="Source credibility updated successfully.")
    except Exception as e:
        current_app.logger.error(f"Error recalculating credibility for {domain}: {str(e)}")
        return make_error_response(f"Server error: {str(e)}", 500)
