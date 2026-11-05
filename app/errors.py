"""Centralised error handling: every error leaves the API in the same JSON shape.

    {"error": {"code": "not_found", "message": "...", "details": {...}, "request_id": "..."}}
"""
from flask import g, jsonify
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from .extensions import db


class AppError(Exception):
    """Base class for expected, client-facing errors. Raise these from anywhere."""

    status_code = 500
    code = "internal_error"
    message = "Internal server error"

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details


class BadRequest(AppError):
    status_code, code, message = 400, "bad_request", "Bad request"


class Unauthorized(AppError):
    status_code, code, message = 401, "unauthorized", "Authentication required"


class Forbidden(AppError):
    status_code, code, message = 403, "forbidden", "You do not have permission"


class NotFound(AppError):
    status_code, code, message = 404, "not_found", "Resource not found"


class Conflict(AppError):
    status_code, code, message = 409, "conflict", "Resource already exists"


def _response(status, code, message, details=None):
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(g, "request_id", None),
        }
    }
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return _response(err.status_code, err.code, err.message, err.details)

    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return _response(422, "validation_error", "Invalid input", err.messages)

    @app.errorhandler(IntegrityError)
    def handle_integrity(err):
        # Catches races the pre-checks miss (e.g. two simultaneous signups).
        db.session.rollback()
        app.logger.warning("IntegrityError: %s", err.orig)
        return _response(409, "conflict", "Resource already exists")

    @app.errorhandler(HTTPException)
    def handle_http(err):
        # Flask/Werkzeug's own 404/405/413... -> JSON instead of HTML
        code = (err.name or "error").lower().replace(" ", "_")
        return _response(err.code, code, err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        app.logger.exception("Unhandled exception")  # full traceback in logs only
        return _response(500, "internal_error", "Internal server error")
