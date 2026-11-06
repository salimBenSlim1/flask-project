"""Request-ID + access logging (Express: morgan + a request-id middleware)."""
import time
from uuid import uuid4

from flask import g, request


def register_request_hooks(app):
    @app.before_request
    def start_request():
        g.request_id = request.headers.get("X-Request-ID") or uuid4().hex
        g.started_at = time.perf_counter()

    @app.after_request
    def finish_request(response):
        started = getattr(g, "started_at", None)
        elapsed_ms = (time.perf_counter() - started) * 1000 if started else 0
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        app.logger.info(
            "%s %s -> %s (%.1fms) rid=%s",
            request.method, request.path, response.status_code, elapsed_ms,
            getattr(g, "request_id", "-"),
        )
        return response
