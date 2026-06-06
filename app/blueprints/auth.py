from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timezone
from app.extensions import db
from app.models.user import User
from app.services.utils import validate_email
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
    elif not validate_email(email):
        errors['email'] = 'Invalid email address format.'
        
    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters long.'
        
    if not confirm_password:
        errors['confirm_password'] = 'Password confirmation is required.'
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
    user.last_login = datetime.now(timezone.utc)
    
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
        return make_error_response("Missing credentials. Email and password required.", 400)

    # Try lookup by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not user.check_password(password):
        return make_error_response("Invalid email or password.", 401)

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log this error or proceed; we shouldn't block login if timestamp update fails
        # but let's make sure it is rolled back
        pass

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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Endpoint to trigger user logout on the backend"""
    # In a stateless JWT architecture, the client destroys the token.
    # We return a standard success response confirming logout.
    return make_success_response(
        message="Logout successful"
    )

