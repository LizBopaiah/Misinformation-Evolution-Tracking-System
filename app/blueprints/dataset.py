from flask import Blueprint, jsonify
from app.services.dataset_service import DatasetService

dataset_bp = Blueprint('dataset', __name__, url_prefix='/api/datasets')

@dataset_bp.route('/status', methods=['GET'])
def get_status():
    service = DatasetService()
    stats = service.validate_datasets() # Uses cache
    
    # Filter to only show status and records count
    result = {}
    for key in ["fake_news", "liar", "emotion"]:
        if key in stats:
            result[key] = {
                "status": stats[key].get("status", "Missing"),
                "records": stats[key].get("records", 0)
            }
    return jsonify(result)

@dataset_bp.route('/statistics', methods=['GET'])
def get_statistics():
    service = DatasetService()
    stats = service.validate_datasets() # Uses cache
    
    # Filter to show labels distribution and missing values
    result = {}
    for key in ["fake_news", "liar", "emotion"]:
        if key in stats:
            result[key] = {
                "labels": stats[key].get("labels", {}),
                "missing_values": stats[key].get("missing_values", 0)
            }
    return jsonify(result)

@dataset_bp.route('/preview', methods=['GET'])
def get_preview():
    service = DatasetService()
    preview = service.get_preview()
    return jsonify(preview)
