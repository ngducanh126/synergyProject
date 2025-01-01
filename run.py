from flask_cors import CORS
from app import create_app, socketio

# Create Flask app instance
app = create_app()

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://synergyprojectfrontend.onrender.com",  # Deployed frontend URL
            "http://localhost:3000"  # Local development URL
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"],
        "expose_headers": ["Authorization"],
        "supports_credentials": True,
    }
})

if __name__ == '__main__':
    # Run the app with SocketIO
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
