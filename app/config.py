import os 

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'your-jwt-secret-key'
    BASE_URL = 'http://127.0.0.1:5000'  # Base URL for serving uploaded files
    UPLOAD_FOLDER_COLLABORATIONS = os.getenv(
        "UPLOAD_FOLDER_COLLABORATIONS",
        os.path.join(os.getcwd(), 'uploads/collaborations'),
    )
    UPLOAD_FOLDER_PROFILE = os.getenv(
        "UPLOAD_FOLDER_PROFILE",
        os.path.join(os.getcwd(), 'uploads/users'),
    )

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
