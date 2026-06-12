import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from app.config import Config
from app.extensions import db, migrate, jwt
from app.blueprints.api import make_error_response

def create_app(config_class=Config):
    """Flask Application Factory Pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Setup Logging directory and handlers
    configure_logging(app)

    # Register API and Frontend Blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Context processors and DB Auto-Creation (For immediate execution out-of-the-box)
    with app.app_context():
        # Imports here to avoid cycle
        import app.models as app_models  # noqa: F401
        try:
            db.create_all()
            app.logger.info("Database initialized successfully (SQLite)")
        except Exception as e:
            app.logger.error(f"Failed to auto-create database: {str(e)}")

        # Trigger dataset validation on startup (will load from cache if available)
        from app.services.dataset_service import DatasetService
        try:
            DatasetService().validate_datasets()
            app.logger.info("Dataset validation completed successfully (loaded or cached)")
        except Exception as e:
            app.logger.error(f"Failed to validate datasets on startup: {str(e)}")

    return app

def configure_logging(app):
    """Configures centralized logging to logs/application.log and console"""
    log_dir = app.config['LOG_DIR']
    os.makedirs(log_dir, exist_ok=True)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Rotating File Handler
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Stream Handler (Stdout)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("MET application logging initialized.")

def register_blueprints(app):
    """Registers authentication, profile, search layers, and frontend main pages"""
    from app.blueprints.auth import auth_bp
    from app.blueprints.user import user_bp
    from app.blueprints.api import api_bp
    from app.blueprints.main import main_bp
    from app.blueprints.dataset import dataset_bp
    from app.blueprints.model import model_bp
    from app.blueprints.nlp import nlp_bp
    from app.blueprints.search import search_bp
    from app.blueprints.sentiment import sentiment_bp
    from app.blueprints.evolution import evolution_bp
    from app.blueprints.research import research_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(nlp_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(sentiment_bp)
    app.register_blueprint(evolution_bp)
    app.register_blueprint(research_bp)


def register_error_handlers(app):
    """Registers global handlers for HTTP error codes to return structured JSON payloads"""
    
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"400 Bad Request: {str(error)}")
        return make_error_response("Bad request parameter or malformed structure.", 400)

    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f"401 Unauthorized: {str(error)}")
        return make_error_response("Authentication credentials are required or invalid.", 401)

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"403 Forbidden: {str(error)}")
        return make_error_response("You do not have permission to access this resource.", 403)

    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"404 Not Found: {str(error)}")
        return make_error_response("The requested resource could not be found.", 404)

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"500 Server Error: {str(error)}", exc_info=True)
        return make_error_response("An unexpected server error occurred.", 500)
        
    @jwt.unauthorized_loader
    def custom_jwt_unauthorized(callback_msg):
        app.logger.warning(f"JWT Unauthorized: {callback_msg}")
        return make_error_response(callback_msg, 401)

    @jwt.invalid_token_loader
    def custom_jwt_invalid(callback_msg):
        app.logger.warning(f"JWT Invalid Token: {callback_msg}")
        return make_error_response(f"Invalid token: {callback_msg}", 401)

    @jwt.expired_token_loader
    def custom_jwt_expired(jwt_header, jwt_payload):
        app.logger.warning(f"JWT Token Expired: {jwt_payload}")
        return make_error_response("The provided access token has expired.", 401)
