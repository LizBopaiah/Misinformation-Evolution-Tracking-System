from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.search import SearchHistory
from app.models.report import ResearchReport, ComparisonResult
from app.services.research_intelligence_service import ResearchIntelligenceService
from app.blueprints.api import make_success_response, make_error_response

research_bp = Blueprint('research', __name__, url_prefix='/api/research')

@research_bp.route('/profile', methods=['POST'])
@jwt_required()
def get_profiles():
    """Generates research profiles for a list of search IDs"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    try:
        data = request.get_json()
    except Exception:
        return make_error_response("Malformed JSON payload.", 400)
        
    search_ids = data.get('search_ids')
    if not search_ids or not isinstance(search_ids, list):
        return make_error_response("search_ids must be a non-empty list of integers.", 400)
        
    # Verify ownership
    for sid in search_ids:
        try:
            sid_int = int(sid)
        except (ValueError, TypeError):
            return make_error_response("Each search_id must be an integer.", 400)
            
        search = db.session.query(SearchHistory).filter_by(id=sid_int, user_id=user_id).first()
        if not search:
            return make_error_response(f"Search history ID {sid_int} not found or access denied.", 404)
            
    try:
        svc = ResearchIntelligenceService()
        profiles = svc.generate_research_profile(search_ids)
        return make_success_response(data=profiles, message="Profiles generated successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to generate search profiles: {str(e)}")
        return make_error_response(f"Profile generation error: {str(e)}", 500)


@research_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_searches():
    """Executes a comparative analytics query and generates a research report snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    try:
        data = request.get_json()
    except Exception:
        return make_error_response("Malformed JSON payload.", 400)
        
    search_ids = data.get('search_ids')
    report_name = data.get('report_name')
    
    if not report_name or not isinstance(report_name, str) or not report_name.strip():
        return make_error_response("report_name field is required.", 400)
        
    if not search_ids or not isinstance(search_ids, list):
        return make_error_response("search_ids field must be a list.", 400)
        
    if len(search_ids) < 2 or len(search_ids) > 10:
        return make_error_response("Comparative analysis requires between 2 and 10 search queries.", 400)

    # Verify ownership of all compared search records
    for sid in search_ids:
        try:
            sid_int = int(sid)
        except (ValueError, TypeError):
            return make_error_response("Each search_id must be an integer.", 400)
            
        search = db.session.query(SearchHistory).filter_by(id=sid_int, user_id=user_id).first()
        if not search:
            return make_error_response(f"Search history ID {sid_int} not found or access denied.", 404)

    try:
        svc = ResearchIntelligenceService()
        report, comparison, cached = svc.generate_comparative_report(search_ids, user_id, report_name.strip())
        
        # Serialize response payload
        report_data = report.to_dict()
        report_data["cached"] = cached
        report_data["shared_themes"] = comparison.shared_themes
        report_data["shared_emotions"] = comparison.shared_emotions
        report_data["shared_claims"] = comparison.shared_claims
        report_data["similarity_score"] = comparison.similarity_score
        
        return make_success_response(
            data=report_data,
            message="Comparative analysis generated successfully."
        )
    except Exception as e:
        current_app.logger.error(f"Failed to generate comparative report: {str(e)}", exc_info=True)
        return make_error_response(f"Comparative report error: {str(e)}", 500)


@research_bp.route('/report/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """Retrieves a cached research report and its comparison metrics"""
    user_id = int(get_jwt_identity())
    
    report = db.session.query(ResearchReport).filter_by(id=report_id, user_id=user_id).first()
    if not report:
        return make_error_response("Research report not found or access denied.", 404)
        
    comparison = db.session.query(ComparisonResult).filter_by(report_id=report_id).first()
    if not comparison:
        return make_error_response("Comparison metrics for this report are missing.", 404)
        
    report_data = report.to_dict()
    report_data["cached"] = True
    report_data["shared_themes"] = comparison.shared_themes
    report_data["shared_emotions"] = comparison.shared_emotions
    report_data["shared_claims"] = comparison.shared_claims
    report_data["similarity_score"] = comparison.similarity_score
    
    return make_success_response(data=report_data, message="Report retrieved successfully.")


@research_bp.route('/reports', methods=['GET'])
@jwt_required()
def list_reports():
    """Lists all research report snapshots created by the user"""
    user_id = int(get_jwt_identity())
    
    reports = db.session.query(ResearchReport).filter_by(user_id=user_id).order_by(ResearchReport.created_at.desc()).all()
    reports_list = []
    
    for r in reports:
        comp = db.session.query(ComparisonResult).filter_by(report_id=r.id).first()
        r_dict = r.to_dict()
        r_dict["similarity_score"] = comp.similarity_score if comp else 0.0
        reports_list.append(r_dict)
        
    return make_success_response(data=reports_list, message="Reports listed successfully.")


@research_bp.route('/report/<int:report_id>/export', methods=['GET'])
@jwt_required()
def export_report(report_id):
    """Exports a comparative report in JSON or HTML/Printable format"""
    user_id = int(get_jwt_identity())
    fmt = request.args.get('format', 'json').lower()
    
    report = db.session.query(ResearchReport).filter_by(id=report_id, user_id=user_id).first()
    if not report:
        return make_error_response("Research report not found or access denied.", 404)
        
    comparison = db.session.query(ComparisonResult).filter_by(report_id=report_id).first()
    if not comparison:
        return make_error_response("Comparison metrics are missing.", 404)
        
    svc = ResearchIntelligenceService()
    profiles = svc.generate_research_profile(report.search_ids)
    
    if fmt == 'json':
        export_data = svc.export_report_to_json(report, comparison, profiles)
        return jsonify(export_data)
    elif fmt == 'pdf' or fmt == 'html':
        # Returns print-ready styled HTML layout
        html_content = svc.export_report_to_html_printable(report, comparison, profiles)
        return Response(html_content, mimetype='text/html')
    else:
        return make_error_response("Unsupported export format. Use 'json' or 'pdf'.", 400)
