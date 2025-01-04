import os
from dotenv import load_dotenv

# Load environment variables from .env (only for local development)
if os.getenv("FLASK_ENV") != "production":
    load_dotenv()
    print("[DEBUG] Loaded .env file for local development.")

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-secret-key")

    # Cloudinary configuration
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

    # Base URL for API calls
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

    # Default upload folder structure
    UPLOAD_FOLDER_COLLABORATIONS = os.getenv("UPLOAD_FOLDER_COLLABORATIONS", "uploads/collaborations")
    UPLOAD_FOLDER_PROFILE = os.getenv("UPLOAD_FOLDER_PROFILE", "uploads/users")
    UPLOAD_ITEM_COLLECTION = os.getenv("UPLOAD_ITEM_COLLECTION", "uploads/collections")
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # CORS
    CORS_ORIGINS = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    print(f"[DEBUG] Raw CORS_ORIGINS from environment: {os.getenv('CORS_ORIGINS')}")
    print(f"[DEBUG] Processed CORS_ORIGINS: {CORS_ORIGINS}")

    # Storage method
    STORAGE_METHOD = os.getenv("STORAGE_METHOD", "local")

    # Debug mode
    DEBUG = os.getenv("FLASK_ENV") != "production"
