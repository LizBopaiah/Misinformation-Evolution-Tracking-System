from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models.user import User
from app.blueprints.api import make_success_response, make_error_response, make_validation_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json() or {}
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    # Map username to email to satisfy database uniqueness rules cleanly
    username = email
    
    errors = {}
    if not full_name:
        errors['full_name'] = 'Full Name is required.'
    if not email:
        errors['email'] = 'Email is required.'
    if not password:
        errors['password'] = 'Password is required.'
    elif password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'
        
    if errors:
        return make_validation_response(errors)

    # Check for existing user
    if User.query.filter_by(email=email).first():
        return make_error_response("Email is already registered.", 400)

    # Create new user
    user = User(username=username, email=email, full_name=full_name)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_error_response(f"Database error during registration: {str(e)}", 500)

    # Automatically generate access token
    access_token = create_access_token(
        identity=str(user.id)
    )

    return make_success_response(
        data={
            "user": user.to_dict(),
            "access_token": access_token
        },
        message="Registration successful",
        status_code=201
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user and return a JWT access token"""
    data = request.get_json() or {}
    
    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')
    
    if not username_or_email or not password:
        return make_error_response("Missing credentials. Username/email and password required.", 400)

    # Try lookup by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not user.check_password(password):
        return make_error_response("Invalid username/email or password.", 401)

    # Generate JWT
    access_token = create_access_token(
        identity=str(user.id)
    )

    return make_success_response(
        data={
            "user": user.to_dict(),
            "access_token": access_token
        },
        message="Login successful"
    )
