from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins=["http://localhost:3000", "http://localhost:3001"])

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    # Import and register Blueprints
    from app.auth_routes import auth_bp
    from app.profile_routes import profile_bp
    from app.match_routes import match_bp
    from app.chat_routes import chat_bp  # Chat routes for real-time messaging

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(match_bp, url_prefix='/match')
    app.register_blueprint(chat_bp, url_prefix='/chat')

    return app
