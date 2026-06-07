from flask import Blueprint, request, jsonify
from app.services.nlp_service import preprocess_text

nlp_bp = Blueprint('nlp', __name__, url_prefix='/api/nlp')

@nlp_bp.route('/preprocess', methods=['POST'])
def preprocess():
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided. Field 'text' is required."}), 400
        
    cleaned = preprocess_text(text)
    return jsonify({
        "original_text": text,
        "processed_text": cleaned
    })
