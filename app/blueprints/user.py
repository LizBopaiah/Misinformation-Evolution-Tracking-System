from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import time
from werkzeug.utils import secure_filename
from PIL import Image
import io
from app.extensions import db
from app.models.user import User
from app.models.search import SearchHistory
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
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')

    errors = {}
    
    # Enforce disabled email editing
    if email and email != user.email:
        errors['email'] = 'Email editing is disabled.'
        return make_validation_response(errors)

    if full_name is not None:
        full_name = full_name.strip()
        if not full_name:
            errors['full_name'] = 'Full Name cannot be empty.'
        else:
            user.full_name = full_name

    if errors:
        return make_validation_response(errors)

    if password:
        if len(password) < 8:
            return make_validation_response({"password": "Password must be at least 8 characters long."})
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

@user_bp.route('/profile-picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    """Upload or update profile picture for the authenticated user"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return make_error_response("User not found.", 404)
        
    if 'profile_picture' not in request.files:
        return make_error_response("No file part provided.", 400)
        
    file = request.files['profile_picture']
    if file.filename == '':
        return make_error_response("No selected file.", 400)
        
    # Validate MIME type
    allowed_mimetypes = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_mimetypes:
        return make_error_response("Invalid file type. Allowed formats: JPG, JPEG, PNG, WEBP.", 400)
        
    # Validate file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return make_error_response("Invalid file extension. Allowed formats: JPG, JPEG, PNG, WEBP.", 400)
        
    # Verify image integrity and size using PIL
    try:
        file_bytes = file.read()
        file.seek(0)
        
        # Enforce file size limit of 5MB
        if len(file_bytes) > current_app.config['MAX_CONTENT_LENGTH']:
            return make_error_response("File size exceeds the 5MB limit.", 400)
            
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        return make_error_response("Corrupted or invalid image file.", 400)
        
    # Generate unique secure filename
    filename = secure_filename(f"user_{user_id}_{int(time.time())}.{ext}")
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    
    # Delete old profile picture if it exists
    if user.profile_picture:
        old_filename = os.path.basename(user.profile_picture)
        old_path = os.path.join(upload_dir, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
                
    # Save the new file
    file_path = os.path.join(upload_dir, filename)
    try:
        file.seek(0)
        file.save(file_path)
    except Exception as e:
        return make_error_response(f"Failed to save profile picture: {str(e)}", 500)
        
    # Update DB
    user.profile_picture = f"/uploads/profile_pictures/{filename}"
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Clean up saved file
        if os.path.exists(file_path):
            os.remove(file_path)
        return make_error_response(f"Database error saving image reference: {str(e)}", 500)
        
    return make_success_response(
        data=user.to_dict(),
        message="Profile picture uploaded successfully."
    )

@user_bp.route('/profile-picture', methods=['DELETE'])
@jwt_required()
def delete_profile_picture():
    """Remove user profile picture and reset to default"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return make_error_response("User not found.", 404)
        
    if not user.profile_picture:
        return make_error_response("No profile picture exists to delete.", 400)
        
    # Delete file from disk
    filename = os.path.basename(user.profile_picture)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    # Reset path in DB
    user.profile_picture = None
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_error_response(f"Database error during deletion: {str(e)}", 500)
        
    return make_success_response(
        data=user.to_dict(),
        message="Profile picture deleted successfully."
    )

@user_bp.route('/search-history', methods=['GET'])
@jwt_required()
def get_search_history():
    """Retrieve search history for the authenticated user"""
    user_id = get_jwt_identity()
    searches = db.session.query(SearchHistory).filter_by(user_id=user_id).order_by(SearchHistory.created_at.desc()).all()
    
    return make_success_response(
        data=[s.to_dict() for s in searches],
        message="Search history retrieved successfully."
    )


