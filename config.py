"""Configuration module for Flask application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development only.
# In Kubernetes, envs come from Secrets and the deployment.
load_dotenv()


def _as_bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    """Configuration class for Flask application."""

    # PostgreSQL configuration (matches Kubernetes Secret -> env injection)
    DB_USER = os.getenv('POSTGRES_USER', 'admin')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'adminpass')
    DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    DB_PORT = os.getenv('POSTGRES_PORT', '5432')
    DB_NAME = os.getenv('POSTGRES_DB', 'database')

    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = (
        f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}'
        f'@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Optional: avoid stale connections after idling
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }

    # Flask runtime configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = _as_bool(os.getenv('FLASK_DEBUG', os.getenv('DEBUG', 'false')), default=False)
    HOST = os.getenv('FLASK_HOST', os.getenv('HOST', '0.0.0.0'))

    # IMPORTANT: default to 5000 to match typical Helm service.port; allow overrides
    PORT = int(os.getenv('FLASK_PORT', os.getenv('PORT', '5000')))

    @classmethod
    def get_database_uri(cls):
        """Get database URI for connection."""
        return cls.SQLALCHEMY_DATABASE_URI

    @classmethod
    def is_debug_mode(cls):
        """Check if debug mode is enabled."""
        return cls.DEBUG
