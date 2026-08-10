from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.case import InvestigationCase, CaseActivity
from app.services.case_service import CaseService
from app.blueprints.api import make_success_response, make_error_response

case_bp = Blueprint('case', __name__, url_prefix='/api/cases')

@case_bp.route('', methods=['POST'])
@jwt_required()
def create_case():
    """Create a new investigation case"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    status = data.get('status', 'OPEN')
    priority = data.get('priority', 'MEDIUM')
    
    if not title or not title.strip():
        return make_error_response("title field is required.", 400)
        
    if status not in ('OPEN', 'ACTIVE', 'COMPLETED', 'ARCHIVED'):
        return make_error_response("Invalid status value.", 400)
        
    if priority not in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
        return make_error_response("Invalid priority value.", 400)
        
    try:
        svc = CaseService()
        case = svc.create_case(user_id, title.strip(), description, status, priority)
        return make_success_response(data=case.to_dict(), message="Investigation case created successfully.", status_code=201)
    except Exception as e:
        current_app.logger.error(f"Failed to create case: {str(e)}", exc_info=True)
        return make_error_response(f"Failed to create case: {str(e)}", 500)

@case_bp.route('', methods=['GET'])
@jwt_required()
def list_cases():
    """List all cases for the current user"""
    user_id = int(get_jwt_identity())
    
    try:
        cases = db.session.query(InvestigationCase).filter_by(user_id=user_id).order_by(InvestigationCase.created_at.desc()).all()
        cases_list = [c.to_dict() for c in cases]
        return make_success_response(data={"cases": cases_list}, message="Cases retrieved successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to list cases: {str(e)}", exc_info=True)
        return make_error_response("Failed to retrieve cases.", 500)

@case_bp.route('/<int:case_id>', methods=['GET'])
@jwt_required()
def get_case_dashboard(case_id):
    """Retrieve case details, paginated linked items, stats, and timeline activities"""
    user_id = int(get_jwt_identity())
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 25, type=int)
    
    # 1. Ownership check (Return 404 to prevent information disclosure)
    case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return make_error_response("Case not found or access denied.", 404)
        
    try:
        svc = CaseService()
        dashboard = svc.get_case_dashboard(case_id, user_id, page=page, page_size=page_size)
        stats = svc.calculate_case_statistics(case_id, user_id)
        
        # Load activity log/timeline
        activities = db.session.query(CaseActivity).filter_by(case_id=case_id).order_by(CaseActivity.created_at.desc()).all()
        
        dashboard["statistics"] = stats
        dashboard["timeline"] = [act.to_dict() for act in activities]
        
        return make_success_response(data=dashboard, message="Case dashboard loaded successfully.")
    except PermissionError as pe:
        return make_error_response(str(pe), 403)
    except Exception as e:
        current_app.logger.error(f"Failed to load case dashboard: {str(e)}", exc_info=True)
        return make_error_response("Failed to load case workspace.", 500)

@case_bp.route('/<int:case_id>', methods=['PUT'])
@jwt_required()
def update_case(case_id):
    """Update case metadata"""
    user_id = int(get_jwt_identity())
    
    # Ownership check
    case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return make_error_response("Case not found or access denied.", 404)
        
    if case.status == 'ARCHIVED':
        return make_error_response("Cannot modify an archived case.", 400)
        
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    updates = {}
    
    if 'title' in data:
        t = data.get('title')
        if not t or not t.strip():
            return make_error_response("title cannot be empty.", 400)
        updates['title'] = t.strip()
        
    if 'description' in data:
        updates['description'] = data.get('description')
        
    if 'status' in data:
        status = data.get('status')
        if status not in ('OPEN', 'ACTIVE', 'COMPLETED', 'ARCHIVED'):
            return make_error_response("Invalid status value.", 400)
        updates['status'] = status
        
    if 'priority' in data:
        priority = data.get('priority')
        if priority not in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
            return make_error_response("Invalid priority value.", 400)
        updates['priority'] = priority
        
    try:
        svc = CaseService()
        updated_case = svc.update_case(case_id, user_id, **updates)
        return make_success_response(data=updated_case.to_dict(), message="Case metadata updated successfully.")
    except PermissionError as pe:
        return make_error_response(str(pe), 403)
    except ValueError as ve:
        return make_error_response(str(ve), 400)
    except Exception as e:
        current_app.logger.error(f"Failed to update case: {str(e)}", exc_info=True)
        return make_error_response("Failed to update case details.", 500)

@case_bp.route('/<int:case_id>', methods=['DELETE'])
@jwt_required()
def archive_case(case_id):
    """Archive a case (never hard delete)"""
    user_id = int(get_jwt_identity())
    
    # Ownership check
    case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return make_error_response("Case not found or access denied.", 404)
        
    try:
        svc = CaseService()
        svc.archive_case(case_id, user_id)
        return make_success_response(message="Case archived successfully.")
    except PermissionError as pe:
        return make_error_response(str(pe), 403)
    except ValueError as ve:
        return make_error_response(str(ve), 400)
    except Exception as e:
        current_app.logger.error(f"Failed to archive case: {str(e)}", exc_info=True)
        return make_error_response("Failed to archive case.", 500)

@case_bp.route('/<int:case_id>/items', methods=['POST'])
@jwt_required()
def add_item_to_case(case_id):
    """Attach an artifact to a case"""
    user_id = int(get_jwt_identity())
    
    # 1. Ownership check
    case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return make_error_response("Case not found or access denied.", 404)
        
    if case.status == 'ARCHIVED':
        return make_error_response("Cannot modify an archived case.", 400)
        
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    item_type = data.get('item_type')
    item_id = data.get('item_id')
    
    if not item_type or not item_id:
        return make_error_response("item_type and item_id fields are required.", 400)
        
    if item_type not in ('search', 'sentiment', 'evolution', 'comparison', 'export'):
        return make_error_response("Unsupported item type.", 400)
        
    try:
        svc = CaseService()
        item = svc.add_item(case_id, user_id, item_type, item_id)
        return make_success_response(data=item.to_dict(), message="Artifact linked to case successfully.")
    except PermissionError as pe:
        # Strict HTTP 403 for ownership violation
        return make_error_response(str(pe), 403)
    except FileNotFoundError as fnf:
        return make_error_response(str(fnf), 404)
    except ValueError as ve:
        return make_error_response(str(ve), 400)
    except Exception as e:
        current_app.logger.error(f"Failed to link artifact: {str(e)}", exc_info=True)
        return make_error_response("Failed to link artifact to case.", 500)

@case_bp.route('/<int:case_id>/items/<string:item_type>/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remove_item_from_case(case_id, item_type, item_id):
    """Detach an artifact from a case"""
    user_id = int(get_jwt_identity())
    
    # Ownership check
    case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return make_error_response("Case not found or access denied.", 404)
        
    if case.status == 'ARCHIVED':
        return make_error_response("Cannot modify an archived case.", 400)
        
    if item_type not in ('search', 'sentiment', 'evolution', 'comparison', 'export'):
        return make_error_response("Unsupported item type.", 400)
        
    try:
        svc = CaseService()
        svc.remove_item(case_id, user_id, item_type, item_id)
        return make_success_response(message="Artifact detached from case successfully.")
    except PermissionError as pe:
        return make_error_response(str(pe), 403)
    except FileNotFoundError as fnf:
        return make_error_response(str(fnf), 404)
    except ValueError as ve:
        return make_error_response(str(ve), 400)
    except Exception as e:
        current_app.logger.error(f"Failed to detach artifact: {str(e)}", exc_info=True)
        return make_error_response("Failed to detach artifact from case.", 500)
