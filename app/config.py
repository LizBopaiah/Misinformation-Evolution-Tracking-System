import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Base Configuration Class"""
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-development-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 1 day in seconds

    # Database configuration
    # Fallback to local sqlite db in root folder
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # External APIs
    GOOGLE_CUSTOM_SEARCH_API_KEY = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY', '')
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    # Central Logging Directory
    LOG_DIR = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'application.log')
