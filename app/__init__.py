from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints or routes
    with app.app_context():
        from app.routes import bp
        app.register_blueprint(bp)

        # Create database tables
        db.create_all()

    return app
