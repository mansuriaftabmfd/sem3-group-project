"""
Configuration Module for SkillVerse Application

This module demonstrates OOP Concept: INHERITANCE
- Base Config class with common settings
- DevelopmentConfig and ProductionConfig inherit from Config
- Each child class can override or extend parent class attributes

Author: SkillVerse Team
Purpose: Centralized configuration management
"""

import os
from datetime import timedelta

# Get the base directory of the application
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Base Configuration Class
    
    OOP Concept: BASE CLASS for inheritance
    Contains common configuration settings used across all environments
    """
    
    # Security: Secret key for session management and CSRF protection
    # In production, this should be a strong random string from environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    # SQLAlchemy will use this URI to connect to the database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:8791@localhost/skillverse_pg'
    
    # Disable SQLAlchemy modification tracking (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Configuration
    # Sessions will expire after 7 days of inactivity
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Upload Configuration
    # Maximum file size for uploads (5MB)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB in bytes
    UPLOAD_FOLDER = os.path.join(basedir, '..', '..', 'FRONTEND', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Pagination
    # Number of items to display per page
    ITEMS_PER_PAGE = 12
    
    # Admin Configuration
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@skillverse.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Email Configuration (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', f"SkillVerse <{os.environ.get('MAIL_USERNAME', '')}>")

    # AskVera AI Assistant
    ENABLE_ASKVERA = os.environ.get('ENABLE_ASKVERA', 'False').lower() == 'true'
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')






class DevelopmentConfig(Config):
    """
    Development Environment Configuration
    
    OOP Concept: INHERITANCE - Inherits from Config class
    Adds development-specific settings
    """
    
    # Enable debug mode for detailed error pages
    DEBUG = True
    
    # Enable testing mode
    TESTING = False
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True  # Log all SQL queries (useful for debugging)


class ProductionConfig(Config):
    """
    Production Environment Configuration
    
    OOP Concept: INHERITANCE - Inherits from Config class
    Overrides settings for production deployment
    """
    
    # Disable debug mode in production for security
    DEBUG = False
    TESTING = False
    
    # Production should use a strong secret key from environment
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Production database (PostgreSQL, MySQL, etc.)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Disable SQL query logging in production
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """
    Testing Environment Configuration
    
    OOP Concept: INHERITANCE - Inherits from Config class
    Used for running automated tests
    """
    
    TESTING = True
    DEBUG = True
    
    # Use SQLite for testing if no URL provided
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///test_db.sqlite'

    
    # Disable CSRF protection in testing
    WTF_CSRF_ENABLED = False


# Dictionary to easily access configurations
# This demonstrates the use of DICTIONARY data structure for configuration management
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name='default'):
    """
    Factory function to get configuration object
    
    Args:
        config_name (str): Name of configuration ('development', 'production', 'testing')
        
    Returns:
        Config: Configuration class object
        
    This function demonstrates:
    - FUNCTION as a factory pattern
    - DICTIONARY lookup for O(1) access time
    """
    return config.get(config_name, config['default'])

