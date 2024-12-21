from flask_cors import CORS
from app import create_app

app = create_app()
CORS(app)  # Add CORS to enable cross-origin requests

if __name__ == '__main__':
    app.run(debug=True)
