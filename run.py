from flask_cors import CORS
from app import create_app, socketio

# Create Flask app instance
app = create_app()

# Configure CORS
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:3000", "http://localhost:3001"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
    "supports_credentials": True
}})


if __name__ == '__main__':
    # Run the app with SocketIO
    socketio.run(app, debug=True, host="127.0.0.1", port=5000)
