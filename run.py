from flask_cors import CORS
from flask import send_from_directory, jsonify
from app import create_app, socketio
import os

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

# Path to the frontend's build directory
frontend_build_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
)

# Serve React frontend for undefined routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Catch-all route for React Router."""
    if os.path.exists(os.path.join(frontend_build_path, path)):
        return send_from_directory(frontend_build_path, path)
    else:
        return send_from_directory(frontend_build_path, 'index.html')

if __name__ == '__main__':
    # Run the app with SocketIO
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
