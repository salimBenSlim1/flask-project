"""Application factory (the Flask equivalent of your Express `app.js` + `server.js`)."""
import logging
import os

from flask import Flask, jsonify
from redis import Redis

from .cli import register_cli, seed_demo_data
from .config import DEFAULT_SECRET, config_map
from .errors import register_error_handlers
from .extensions import cors, db
from .middleware.request_context import register_request_hooks
from .routes import register_blueprints


def _enable_pgvector(app: Flask) -> None:
    if db.engine.dialect.name != "postgresql":
        return
    try:
        with db.engine.begin() as conn:
            conn.execute(db.text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception:
        app.logger.exception("Could not enable pgvector. Run `CREATE EXTENSION vector;` as a DB admin.")


def create_app(env: str | None = None) -> Flask:
    env = env or os.environ.get("APP_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_map[env])
    app.config["APP_ENV"] = env

    if env == "production" and app.config["SECRET_KEY"] == DEFAULT_SECRET:
        raise RuntimeError("SECRET_KEY must be set in production")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401  (register models with SQLAlchemy metadata)

    register_request_hooks(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)

    # Lazy client: no connection is made until first command
    app.extensions["redis"] = Redis.from_url(app.config["REDIS_URL"], socket_connect_timeout=2)

    with app.app_context():
        _enable_pgvector(app)
        db.create_all()  # fine for learning; use Flask-Migrate (Alembic) in real projects
        if app.config["SEED_ON_START"]:
            seed_demo_data()  # idempotent demo users (set SEED_ON_START=false to disable)

    @app.get("/health")
    def health():
        checks = {}
        try:
            db.session.execute(db.text("SELECT 1"))
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "down"
        try:
            app.extensions["redis"].ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "down"
        healthy = all(v == "ok" for v in checks.values())
        return jsonify({"status": "ok" if healthy else "degraded", **checks}), 200 if healthy else 503

    return app
