import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()  # like `dotenv.config()` in Node

DEFAULT_SECRET = "dev-secret-change-me"

# The pgvector column size is fixed when the table is created, so it must match your embedding model.
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))
_MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))


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

    # --- RAG ---
    # Keep these variable names for the existing Render environment; their values configure Groq.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "openai/gpt-oss-20b")
    EMBEDDINGS_PROVIDER = os.environ.get("EMBEDDINGS_PROVIDER", "fastembed")  # fastembed|voyage|openai|hashing
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIM = EMBEDDING_DIM
    MAX_UPLOAD_MB = _MAX_UPLOAD_MB
    MAX_CONTENT_LENGTH = (_MAX_UPLOAD_MB + 1) * 1024 * 1024  # +1MB multipart overhead
    MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "200"))
    MAX_DOCS_PER_USER = int(os.environ.get("MAX_DOCS_PER_USER", "10"))
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150
    TOP_K = int(os.environ.get("TOP_K", "5"))
    ASK_RATE_LIMIT = int(os.environ.get("ASK_RATE_LIMIT", "20"))  # questions per minute per user
    INGEST_SYNC = os.environ.get("INGEST_SYNC", "false").lower() == "true"  # tests: no threads


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SEED_ON_START = False
    EMBEDDINGS_PROVIDER = "hashing"
    INGEST_SYNC = True
    ANTHROPIC_API_KEY = "test-key"
    SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
