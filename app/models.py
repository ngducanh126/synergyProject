from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    skills = db.Column(db.ARRAY(db.String), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    availability = db.Column(db.String(50), nullable=True)
    last_active = db.Column(db.DateTime, nullable=True)
    verification_status = db.Column(db.Boolean, default=False)
