import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()  # like `dotenv.config()` in Node

DEFAULT_SECRET = "dev-secret-change-me"


def _database_url() -> str:
    """Render/Heroku-style URLs start with postgres:// or postgresql://; SQLAlchemy needs a driver."""
    url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET)
    SQLALCHEMY_DATABASE_URI = _database_url()
    SEED_ON_START = os.environ.get("SEED_ON_START", "false").lower() == "true"
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    JWT_ACCESS_TTL = timedelta(minutes=15)
    JWT_REFRESH_TTL = timedelta(days=7)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SEED_ON_START = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
