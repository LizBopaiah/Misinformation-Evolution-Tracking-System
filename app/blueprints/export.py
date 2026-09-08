from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, decode_token
from datetime import datetime, timedelta
import os
import hashlib
from app.extensions import db
from app.models.export import ExportRecord
from app.models.search import SearchHistory
from app.models.report import ResearchReport
from app.services.export_service import ExportService
from app.blueprints.api import make_success_response, make_error_response

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

def check_rate_limits(user_id, export_type=None, source_type=None, source_id=None, export_format=None):
    """Enforces 5s window and 50/day limits for export generation requests, bypassing on cache hits"""
    now = datetime.utcnow()
    
    # Bypass rate limits if a completed cache hit exists
    if export_type and source_type and source_id and export_format:
        cached = ExportRecord.query.filter_by(
            user_id=user_id,
            export_type=export_type,
            source_type=source_type,
            source_id=source_id,
            export_format=export_format,
            status='completed'
        ).first()
        if cached and os.path.exists(cached.file_path):
            return True, ""
    
    # 1. 5 seconds limit check
    last_export = db.session.query(ExportRecord).filter_by(user_id=user_id).order_by(ExportRecord.created_at.desc()).first()
    if last_export:
        time_diff = (now - last_export.created_at).total_seconds()
        if time_diff < 5:
            return False, "Rate limit exceeded. Please wait 5 seconds between export requests."

    # 2. Daily cap check (50 exports/day)
    one_day_ago = now - timedelta(days=1)
    daily_count = db.session.query(ExportRecord).filter(
        ExportRecord.user_id == user_id,
        ExportRecord.created_at >= one_day_ago
    ).count()
    
    if daily_count >= 50:
        return False, "Daily export limit reached (maximum 50 per day)."

    return True, ""

@export_bp.route('/fact-audit', methods=['POST'])
@jwt_required()
def export_fact_audit():
    """Generates fact audit export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    search_id = data.get('search_id')
    export_format = data.get('format', 'pdf').lower()

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search record not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'fact_audit', 'search', search_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'fact_audit', 'search', search_id, export_format)
        return make_success_response(data=record.to_dict(), message="Fact audit export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile fact audit export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/sentiment', methods=['POST'])
@jwt_required()
def export_sentiment():
    """Generates sentiment export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    search_id = data.get('search_id')
    export_format = data.get('format', 'pdf').lower()

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search record not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'sentiment', 'search', search_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'sentiment', 'search', search_id, export_format)
        return make_success_response(data=record.to_dict(), message="Sentiment export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile sentiment export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/evolution', methods=['POST'])
@jwt_required()
def export_evolution():
    """Generates narrative evolution export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    search_id = data.get('search_id')
    export_format = data.get('format', 'pdf').lower()

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search record not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'evolution', 'search', search_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'evolution', 'search', search_id, export_format)
        return make_success_response(data=record.to_dict(), message="Evolution export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile evolution export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/comparison', methods=['POST'])
@jwt_required()
def export_comparison():
    """Generates comparative report export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    report_id = data.get('report_id')
    export_format = data.get('format', 'pdf').lower()

    if not report_id:
        return make_error_response("report_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    report = db.session.query(ResearchReport).filter_by(id=report_id, user_id=user_id).first()
    if not report:
        return make_error_response("Research report not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'comparison', 'report', report_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'comparison', 'report', report_id, export_format)
        return make_success_response(data=record.to_dict(), message="Comparative report export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile comparison export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/dossier', methods=['POST'])
@jwt_required()
def export_dossier():
    """Generates full research evidence dossier export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    search_id = data.get('search_id')
    export_format = data.get('format', 'pdf').lower()

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search record not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'dossier', 'search', search_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'dossier', 'search', search_id, export_format)
        return make_success_response(data=record.to_dict(), message="Research dossier export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile dossier export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/explainability', methods=['POST'])
@jwt_required()
def export_explainability():
    """Generates explainability export snapshot"""
    user_id = int(get_jwt_identity())
    
    if not request.is_json:
        return make_error_response("Content-Type must be application/json.", 400)
        
    data = request.get_json()
    search_id = data.get('search_id')
    export_format = data.get('format', 'pdf').lower()

    if not search_id:
        return make_error_response("search_id field is required.", 400)
    if export_format not in ('pdf', 'json', 'html'):
        return make_error_response("Unsupported format. Use 'pdf', 'json', or 'html'.", 400)

    # Ownership check
    search = db.session.query(SearchHistory).filter_by(id=search_id, user_id=user_id).first()
    if not search:
        return make_error_response("Search record not found or access denied.", 404)

    # Check rate limit
    allowed, msg = check_rate_limits(user_id, 'explainability', 'search', search_id, export_format)
    if not allowed:
        return make_error_response(msg, 429)

    try:
        svc = ExportService()
        record = svc.get_or_create_export(user_id, 'explainability', 'search', search_id, export_format)
        return make_success_response(data=record.to_dict(), message="Explainability export compiled successfully.")
    except Exception as e:
        current_app.logger.error(f"Failed to compile explainability export: {str(e)}", exc_info=True)
        return make_error_response(f"Export failed: {str(e)}", 500)

@export_bp.route('/<int:export_id>/<path:filename>', methods=['GET'])
@export_bp.route('/<int:export_id>', methods=['GET'])
def download_export(export_id, filename=None):
    """Streams the requested file with user validation and integrity hash checks"""
    user_id = None
    
    # 1. Try standard header / cookie JWT verification
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
    except Exception:
        pass

    # 2. Try query parameter token (?token=...)
    if not user_id:
        token = request.args.get('token')
        if token:
            try:
                decoded = decode_token(token)
                user_id = int(decoded['sub'])
            except Exception:
                return make_error_response("Invalid or expired download token.", 401)

    if not user_id:
        return make_error_response("Authorization credentials are required.", 401)

    record = db.session.query(ExportRecord).filter_by(id=export_id, user_id=user_id).first()
    if not record:
        return make_error_response("Export record not found or access denied.", 404)

    # Check if file exists on disk, recover if missing
    if not os.path.exists(record.file_path):
        try:
            svc = ExportService()
            svc._write_file_from_snapshot(record)
        except Exception as e:
            return make_error_response(f"File recovery failed: {str(e)}", 500)

    # Verify SHA256 file hash before streaming
    sha256 = hashlib.sha256()
    try:
        with open(record.file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        file_hash = sha256.hexdigest()
    except Exception as e:
        return make_error_response(f"Failed to read file for hash check: {str(e)}", 500)

    if file_hash != record.file_hash:
        current_app.logger.error(f"Integrity check failed: file hash mismatch for export ID {export_id}")
        return make_error_response("Integrity verification failed. The file is corrupted or modified.", 400)

    # Ensure local machine Downloads folder sync
    try:
        import shutil
        dl_folders = [
            os.path.expanduser(r'~\Downloads'),
            r'C:\Users\laksh\Downloads',
            r'C:\Users\laksh\workspace\Downloads'
        ]
        for dl_dir in dl_folders:
            if os.path.exists(dl_dir) and os.path.exists(record.file_path):
                shutil.copyfile(record.file_path, os.path.join(dl_dir, record.file_name))
    except Exception:
        pass

    # Safely download and stream without exposing internal folder paths
    # Set appropriate mimetype
    mimetypes = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'json': 'application/json',
        'html': 'text/html'
    }
    mimetype = mimetypes.get(record.export_format.lower(), 'application/pdf')

    is_inline = request.args.get('inline') == '1'
    disposition = 'inline' if is_inline else 'attachment'

    response = send_file(
        record.file_path,
        mimetype=mimetype,
        as_attachment=(not is_inline),
        download_name=record.file_name
    )
    response.headers['Content-Disposition'] = f'{disposition}; filename="{record.file_name}"; filename*=UTF-8\'\'{record.file_name}'
    response.headers['Content-Type'] = mimetype
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Type'
    return response

@export_bp.route('/history', methods=['GET'])
@jwt_required()
def export_history():
    """Lists export snapshots created by the user"""
    user_id = int(get_jwt_identity())
    records = db.session.query(ExportRecord).filter_by(user_id=user_id).order_by(ExportRecord.created_at.desc()).all()
    
    # Calculate storage stats
    total_size = sum([r.file_size or 0 for r in records])
    history_list = [r.to_dict() for r in records]
    
    return make_success_response(data={
        "history": history_list,
        "total_size_bytes": total_size
    }, message="Export history retrieved successfully.")

@export_bp.route('/<int:export_id>', methods=['DELETE'])
@jwt_required()
def delete_export(export_id):
    """Deletes the export metadata record and removes the physical file from disk"""
    user_id = int(get_jwt_identity())
    
    record = db.session.query(ExportRecord).filter_by(id=export_id, user_id=user_id).first()
    if not record:
        return make_error_response("Export record not found or access denied.", 404)

    # Delete file from disk
    if os.path.exists(record.file_path):
        try:
            os.remove(record.file_path)
        except Exception as e:
            current_app.logger.warning(f"Failed to delete file from disk: {str(e)}")

    db.session.delete(record)
    db.session.commit()
    
    return make_success_response(message="Export record and cached file deleted successfully.")
