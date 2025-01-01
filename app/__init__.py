import os
from flask import Flask, send_from_directory
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

    # Resolve path to the 'uploads' folder (relative to the project root)
    uploads_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

    @app.route('/uploads/<path:filename>', methods=['GET'])
    def serve_upload(filename):
        """Serve files from the uploads directory."""
        full_path = os.path.join(uploads_folder, filename)
        print(f"[DEBUG] Serving file from uploads folder: {full_path}")
        if not os.path.exists(full_path):
            print(f"[ERROR] File not found: {full_path}")
            return {"error": "File not found"}, 404
        return send_from_directory(uploads_folder, filename)

    # Add the new route here
    @app.route('/')
    def home():
        return {"message": "Welcome to the Synergy Project API!"}, 200

    # Import and register Blueprints
    from app.auth_routes import auth_bp
    from app.profile_routes import profile_bp
    from app.match_routes import match_bp
    from app.chat_routes import chat_bp
    from app.collaboration_routes import collaboration_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(match_bp, url_prefix='/match')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(collaboration_bp, url_prefix='/collaboration')

    return app

