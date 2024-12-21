from app import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    bio = db.Column(db.String(255), nullable=True)
    skills = db.Column(db.ARRAY(db.String), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    availability = db.Column(db.String(100), nullable=True)
    verification_status = db.Column(db.Boolean, default=False)
