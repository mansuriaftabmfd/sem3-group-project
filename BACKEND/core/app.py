"""
Main Flask Application for SkillVerse

This is the entry point of the application.
Demonstrates OOP Concept: APPLICATION FACTORY PATTERN

Author: SkillVerse Team
Purpose: Initialize and configure Flask application
"""

from flask import Flask, render_template
from flask_login import LoginManager
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from config import get_config
from models import db, User

# Initialize Flask-Login and Flask-Mail
from extensions import login_manager, oauth, socketio, mail
from flask_compress import Compress




# Initialize Compress
compress = Compress()

def create_app(config_name='default'):
    """
    Application Factory Function
    
    OOP Concept: FACTORY PATTERN
    - Creates and configures Flask application instance
    - Allows multiple app instances with different configurations
    
    Args:
        config_name (str): Configuration name ('development', 'production', 'testing')
        
    Returns:
        Flask: Configured Flask application
    """
    
    # Compute absolute paths to FRONTEND folder (2 levels up from BACKEND/core)
    _core_dir = os.path.abspath(os.path.dirname(__file__))
    _frontend_dir = os.path.abspath(os.path.join(_core_dir, '..', '..', 'FRONTEND'))

    # Create Flask application instance with correct template and static folders
    app = Flask(
        __name__,
        template_folder=os.path.join(_frontend_dir, 'templates'),
        static_folder=os.path.join(_frontend_dir, 'static'),
        static_url_path='/static'
    )
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    oauth.init_app(app)
    mail.init_app(app)
    compress.init_app(app)




    # Performance: Cache Static Files for 1 Year
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
    app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/javascript', 'application/json', 'application/javascript']
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500

    # Register Google OAuth
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'  # Redirect to login page if not authenticated
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """
        Load user by ID for Flask-Login
        
        Args:
            user_id (str): User ID
            
        Returns:
            User: User object or None
        """
        return User.query.get(int(user_id))
    
    # Register blueprints (routes)
    from routes import main_bp, auth_bp, service_bp, user_bp, admin_bp, api_bp, availability_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(service_bp, url_prefix='/service')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(availability_bp, url_prefix='/availability')
    
    # AskVera Chatbot
    from routes_chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()  # Rollback any failed database transactions
        return render_template('errors/500.html'), 500
    
    # Create upload folder if it doesn't exist
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder and not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Migrate: Add is_approved and rejection_reason columns if missing
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'services' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('services')]
            if 'is_approved' not in columns:
                db.session.execute(text('ALTER TABLE services ADD COLUMN is_approved BOOLEAN DEFAULT TRUE'))
                db.session.execute(text('ALTER TABLE services ADD COLUMN rejection_reason VARCHAR(500)'))
                db.session.execute(text('UPDATE services SET is_approved = TRUE'))
                db.session.commit()
        
        # Run Schema Migrations (certificates, wallet_balance, etc.)
        from migrate_db import run_migrations
        run_migrations(app)

        # Create default admin user if not exists
        from init_db import create_default_admin, seed_categories
        create_default_admin(app)
        seed_categories()
    
    # Register Socket.IO events
    from events import register_socketio_events
    register_socketio_events(socketio)
    
    # Template filter for IST conversion
    from datetime import timedelta
    import pytz
    @app.template_filter('to_ist')
    def to_ist(dt):
        if dt:
            # If datetime is naive (no timezone), assume UTC
            if dt.tzinfo is None:
                utc_tz = pytz.UTC
                dt = utc_tz.localize(dt)
            # Convert to IST
            ist_tz = pytz.timezone('Asia/Kolkata')
            return dt.astimezone(ist_tz)
        return dt
    
    return app


if __name__ == '__main__':
    """
    Run the application
    
    This block only executes when running this file directly
    (not when importing as a module)
    """
    
    # Get configuration from environment variable or use default
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create application instance
    app = create_app(config_name)
    
    # Run development server with SocketIO
    # In production, use a WSGI server like Gunicorn or uWSGI
    socketio.run(
        app,
        host='0.0.0.0',  # Listen on all network interfaces
        port=5000,        # Port number
        debug=app.config.get('DEBUG', False),
        allow_unsafe_werkzeug=True
    )