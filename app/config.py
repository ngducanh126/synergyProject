import os
from dotenv import load_dotenv

# Load environment variables from .env (only for local development)
if os.getenv("FLASK_ENV") != "production":
    load_dotenv()
    print("[DEBUG] Loaded .env file for local development.")

class Config:
    """Base configuration."""

    # Load and print all environment variables for debugging
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    print(f"[DEBUG] SECRET_KEY: {SECRET_KEY}")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    print(f"[DEBUG] DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-secret-key")
    print(f"[DEBUG] JWT_SECRET_KEY: {JWT_SECRET_KEY}")

    # Cloudinary configuration
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
    print(f"[DEBUG] CLOUDINARY_URL: {CLOUDINARY_URL}")

    # Base URL for API calls
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
    print(f"[DEBUG] BASE_URL: {BASE_URL}")

    # Default upload folder structure
    UPLOAD_FOLDER_COLLABORATIONS = os.getenv("UPLOAD_FOLDER_COLLABORATIONS", "uploads/collaborations")
    print(f"[DEBUG] UPLOAD_FOLDER_COLLABORATIONS: {UPLOAD_FOLDER_COLLABORATIONS}")

    UPLOAD_FOLDER_PROFILE = os.getenv("UPLOAD_FOLDER_PROFILE", "uploads/users")
    print(f"[DEBUG] UPLOAD_FOLDER_PROFILE: {UPLOAD_FOLDER_PROFILE}")

    UPLOAD_ITEM_COLLECTION = os.getenv("UPLOAD_ITEM_COLLECTION", "uploads/collections")
    print(f"[DEBUG] UPLOAD_ITEM_COLLECTION: {UPLOAD_ITEM_COLLECTION}")

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    print(f"[DEBUG] ALLOWED_EXTENSIONS: {ALLOWED_EXTENSIONS}")

    # CORS
    CORS_ORIGINS = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    print(f"[DEBUG] Raw CORS_ORIGINS from environment: {os.getenv('CORS_ORIGINS')}")
    print(f"[DEBUG] Processed CORS_ORIGINS: {CORS_ORIGINS}")

    # Storage method
    STORAGE_METHOD = os.getenv("STORAGE_METHOD", "local")
    print(f"[DEBUG] STORAGE_METHOD: {STORAGE_METHOD}")

    # Debug mode
    DEBUG = os.getenv("FLASK_ENV") != "production"
    print(f"[DEBUG] FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"[DEBUG] DEBUG mode: {DEBUG}")
