"""
SkillVerse Application Runner
Run this file from root directory to start the application
"""
import sys
import os

# Store the absolute root directory BEFORE any chdir
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# Add BACKEND folders to Python path (using absolute paths)
sys.path.insert(0, os.path.join(ROOT_DIR, 'BACKEND', 'core'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'BACKEND', 'models'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'BACKEND', 'routes'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'BACKEND', 'services'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'BACKEND', 'database'))
sys.path.insert(0, ROOT_DIR)

# Change to BACKEND/core directory for proper template/static paths
os.chdir(os.path.join(ROOT_DIR, 'BACKEND', 'core'))

# Import and run the app
from app import create_app
from extensions import socketio

if __name__ == '__main__':
    print("=" * 60)
    print("SkillVerse Application Starting...")
    print("=" * 60)
    print("Working Directory:", os.getcwd())
    print("URL: http://localhost:5000")
    print("Admin Login: admin@skillverse.com / admin123")
    print("=" * 60)
    
    # Create app instance
    app = create_app('development')
    
    # Run with SocketIO - use_reloader=False prevents the chdir reloader crash
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, 
                 allow_unsafe_werkzeug=True, use_reloader=False)
