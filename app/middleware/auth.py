"""Auth middleware as decorators (Flask's equivalent of Express per-route middleware)."""
from functools import wraps

from flask import g, request

from ..errors import Forbidden, Unauthorized
from ..extensions import db
from ..models import User
from ..services.tokens import ACCESS, decode_token


def _extract_bearer() -> str:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise Unauthorized("Missing or malformed Authorization header")
    return token.strip()


def login_required(fn):
    """Verifies the access token and sets `g.current_user` (like `req.user`)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = decode_token(_extract_bearer(), ACCESS)
        user = db.session.get(User, int(payload["sub"]))
        if user is None:
            raise Unauthorized("User no longer exists")
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """Use *under* login_required:  @login_required then @roles_required('admin')."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.current_user.role not in roles:
                raise Forbidden()
            return fn(*args, **kwargs)

        return wrapper

    return decorator
