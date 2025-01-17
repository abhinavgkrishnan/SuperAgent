import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from models import db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(test_config=None):
    """Application factory function"""
    app = Flask(__name__)

    # Configure the application
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    )

    if test_config is not None:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

    # Import routes after db initialization
    from routes import init_routes

    # Create tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

        # Initialize routes after database setup
        init_routes(app)
        logger.info("Routes initialized successfully")

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)