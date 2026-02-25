from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO
from flask_mail import Mail

# Initialize extensions
login_manager = LoginManager()
oauth = OAuth()
socketio = SocketIO(cors_allowed_origins="*")
mail = Mail()
