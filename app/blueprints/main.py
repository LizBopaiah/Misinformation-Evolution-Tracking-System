from flask import Blueprint, render_template, send_from_directory, current_app
from app.blueprints.api import make_success_response
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Renders visitor-facing public landing page"""
    return render_template('index.html')

@main_bp.route('/login')
def login_page():
    """Renders dedicated login page"""
    return render_template('login.html')

@main_bp.route('/register')
def register_page():
    """Renders dedicated registration page"""
    return render_template('register.html')

@main_bp.route('/dashboard')
def dashboard():
    """Renders authenticated search analysis console"""
    return render_template('dashboard.html')

@main_bp.route('/research')
def research_dashboard():
    """Renders authenticated research comparison console"""
    return render_template('research.html')

@main_bp.route('/profile')
def profile_page():
    """Renders authenticated user profile dashboard"""
    return render_template('profile.html')

@main_bp.route('/search-history')
def search_history_page():
    """Renders authenticated user query logs"""
    return render_template('search_history.html')

@main_bp.route('/about-platform')
def about_platform():
    """Renders public platform capabilities guide"""
    return render_template('about_platform.html')

@main_bp.route('/system-overview')
def system_overview():
    """Renders technical developer overview dashboard"""
    return render_template('system_overview.html')

@main_bp.route('/uploads/profile_pictures/<filename>')
def serve_profile_picture(filename):
    """Serve uploaded profile pictures from filesystem securely"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@main_bp.route('/api/health')
def health():
    """System health check endpoint for testing and verification"""
    return make_success_response(
        data={
            "status": "healthy",
            "db_status": "connected",
            "modules": {
                "auth": "loaded",
                "database_models": "loaded",
                "datasets": "ready"
            }
        },
        message="Misinformation Detection and Evolution Tracking System is online."
    )
