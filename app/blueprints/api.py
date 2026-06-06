from flask import jsonify, Blueprint

api_bp = Blueprint('api_foundation', __name__)

def make_success_response(data=None, message="Operation successful", status_code=200):
    """Returns a standardized JSON success response"""
    return jsonify({
        "success": True,
        "message": message,
        "data": data if data is not None else {}
    }), status_code

def make_error_response(message="An error occurred", status_code=400, errors=None):
    """Returns a standardized JSON error response"""
    response = {
        "success": False,
        "message": message
    }
    if errors is not None:
        response["errors"] = errors
    return jsonify(response), status_code

def make_validation_response(errors, message="Validation failed", status_code=422):
    """Returns a standardized JSON validation response"""
    return make_error_response(message=message, status_code=status_code, errors=errors)
