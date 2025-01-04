from flask_cors import CORS
from flask import send_from_directory
from app import create_app, socketio
import os
from app.config import config  # Import the correct configuration

# Create Flask app instance
app = create_app()

# Dynamically configure CORS
CORS(app, resources={
    r"/*": {
        "origins": config.CORS_ORIGINS,  # Use dynamically loaded origins
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"],
        "expose_headers": ["Authorization"],
        "supports_credentials": True,
    }
})

# Log the environment and allowed CORS origins
if os.getenv("FLASK_ENV") == "development":
    print("[INFO] Running locally in development mode")
else:
    print("[INFO] Running in production mode")

print(f"[INFO] Allowed CORS Origins: {config.CORS_ORIGINS}")

# Serve React frontend for undefined routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Catch-all route for React Router."""
    frontend_build_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    )
    if os.path.exists(os.path.join(frontend_build_path, path)):
        return send_from_directory(frontend_build_path, path)
    else:
        return send_from_directory(frontend_build_path, 'index.html')

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV") == "development"
    print(f"[INFO] Debug mode is {'on' if debug_mode else 'off'}")
    socketio.run(app, debug=debug_mode, host="0.0.0.0", port=5000)
