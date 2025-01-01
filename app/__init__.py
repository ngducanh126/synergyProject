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

    # Create tables if they don't exist
    with app.app_context():
        create_tables()

    # Import and register Blueprints
    from app.auth_routes import auth_bp
    from app.profile_routes import profile_bp
    from app.match_routes import match_bp
    from app.chat_routes import chat_bp
    from app.collaboration_routes import collaboration_bp  # Import moved inside

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(match_bp, url_prefix='/match')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(collaboration_bp, url_prefix='/collaboration')  # Register here

    return app


def create_tables():
    table_creation_statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            likes INTEGER[] DEFAULT '{}',
            bio TEXT,
            skills TEXT[],
            location VARCHAR(255),
            availability VARCHAR(255),
            swipe_right INTEGER[] DEFAULT '{}',
            swipe_left INTEGER[] DEFAULT '{}',
            matches INTEGER[] DEFAULT '{}',
            preferred_medium TEXT[],
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verification_status BOOLEAN DEFAULT FALSE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collaborations (
            id SERIAL PRIMARY KEY,
            admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS user_collaborations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,
            role VARCHAR(255) DEFAULT 'member'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collaboration_photos (
            id SERIAL PRIMARY KEY,
            collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,
            photo_path TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collections (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collection_items (
            id SERIAL PRIMARY KEY,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS collaboration_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            user1_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            user2_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_match_pair
        ON matches (LEAST(user1_id, user2_id), GREATEST(user1_id, user2_id));
        """
    ]

    with db.session.begin():
        for statement in table_creation_statements:
            db.session.execute(statement)

