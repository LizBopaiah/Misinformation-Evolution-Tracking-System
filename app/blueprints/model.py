import os
import json
from flask import Blueprint, jsonify
from app.services.model_service import ModelService

model_bp = Blueprint('model', __name__, url_prefix='/api/models')

@model_bp.route('/status', methods=['GET'])
def get_status():
    service = ModelService()
    status = service.check_models_status()
    return jsonify(status)

@model_bp.route('/performance', methods=['GET'])
def get_performance():
    service = ModelService()
    metrics_path = os.path.join(service.models_dir, "performance_metrics.json")
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Failed to load performance metrics: {str(e)}"}), 500
    else:
        return jsonify({
            "error": "Performance metrics file not found. Please run scripts/train_models.py to train baseline models."
        }), 404
