import os
from dotenv import load_dotenv

# Load environment variables from the `.env` file in the root directory
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-secret-key")

    # Cloudinary configuration
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

    BASE_URL = 'http://127.0.0.1:5000'  # Used for serving local files

    UPLOAD_FOLDER_COLLABORATIONS = os.getenv(
        "UPLOAD_FOLDER_COLLABORATIONS",
        os.path.join(os.getcwd(), 'uploads/collaborations'),
    )
    UPLOAD_FOLDER_PROFILE = os.getenv(
        "UPLOAD_FOLDER_PROFILE",
        os.path.join(os.getcwd(), 'uploads/users'),
    )
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}