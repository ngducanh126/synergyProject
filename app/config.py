import os
from dotenv import load_dotenv

# Load environment variables from .env (only for local development)
if os.getenv("FLASK_ENV") != "production":
    load_dotenv()
    print("[DEBUG] Loaded .env file for local development.")

class Config:
    """Base configuration."""

    # General settings
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    print(f"[DEBUG] SECRET_KEY: {SECRET_KEY}")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    print(f"[DEBUG] DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-secret-key")
    print(f"[DEBUG] JWT_SECRET_KEY: {JWT_SECRET_KEY}")

    # AWS S3 configuration
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    AWS_BUCKET_NAME = os.getenv("BUCKET_NAME")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

    print(f"[DEBUG] AWS_ACCESS_KEY: {AWS_ACCESS_KEY}")
    print(f"[DEBUG] AWS_BUCKET_NAME: {AWS_BUCKET_NAME}")
    print(f"[DEBUG] AWS_REGION: {AWS_REGION}")

    # Base URL for API calls
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
    print(f"[DEBUG] BASE_URL: {BASE_URL}")

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    print(f"[DEBUG] ALLOWED_EXTENSIONS: {ALLOWED_EXTENSIONS}")

    # CORS configuration
    CORS_ORIGINS = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    ]
    print(f"[DEBUG] Raw CORS_ORIGINS from environment: {os.getenv('CORS_ORIGINS')}")
    print(f"[DEBUG] Processed CORS_ORIGINS: {CORS_ORIGINS}")

    # Debug mode
    DEBUG = os.getenv("FLASK_ENV") != "production"
    print(f"[DEBUG] FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"[DEBUG] DEBUG mode: {DEBUG}")
