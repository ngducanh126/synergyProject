import os 

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:hanoihue@localhost:5432/synergy'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'your-jwt-secret-key'
    BASE_URL = 'http://127.0.0.1:5000'  # Base URL for serving uploaded files
    UPLOAD_FOLDER_COLLABORATIONS = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads/collaborations')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
