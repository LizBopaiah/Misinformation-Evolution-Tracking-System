from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from functools import wraps
from app.extensions import db
from app.models.user import User
from app.blueprints.api import make_success_response, make_error_response, make_validation_response

user_bp = Blueprint('user', __name__, url_prefix='/api/users')

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Retrieve current logged in user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return make_error_response("User not found.", 404)
        
    return make_success_response(
        data=user.to_dict(),
        message="Profile retrieved successfully"
    )

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current logged in user profile details"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return make_error_response("User not found.", 404)

    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    errors = {}
    
    # Optional updates validation
    if username:
        existing = User.query.filter_by(username=username).first()
        if existing and str(existing.id) != str(user_id):
            errors['username'] = 'Username is already taken.'
        else:
            user.username = username

    if email:
        existing = User.query.filter_by(email=email).first()
        if existing and str(existing.id) != str(user_id):
            errors['email'] = 'Email is already taken.'
        else:
            user.email = email
            
    if errors:
        return make_validation_response(errors)

    if password:
        user.set_password(password)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_error_response(f"Database error during update: {str(e)}", 500)

    return make_success_response(
        data=user.to_dict(),
        message="Profile updated successfully"
    )

