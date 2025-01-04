from flask_cors import CORS
from flask import send_from_directory
from app import create_app, socketio
import os
from app.config import Config

# Create Flask app instance
app = create_app()

# Dynamically configure CORS
CORS(app, resources={
    r"/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"],
        "expose_headers": ["Authorization"],
        "supports_credentials": True,
    }
})

# Log the environment and allowed CORS origins
print(f"[INFO] Running in {'production' if os.getenv('FLASK_ENV') == 'production' else 'development'} mode")
print(f"[INFO] Allowed CORS Origins: {Config.CORS_ORIGINS}")

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
    debug_mode = Config.DEBUG
    print(f"[INFO] Debug mode is {'on' if debug_mode else 'off'}")
    socketio.run(app, debug=debug_mode, host="0.0.0.0", port=5000)
