from flask_cors import CORS
from app import create_app, socketio

app = create_app()

# Allow CORS for multiple origins (frontend servers)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}})

if __name__ == '__main__':
    socketio.run(app, debug=True, host="127.0.0.1", port=5000)
