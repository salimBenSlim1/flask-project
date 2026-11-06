from datetime import UTC, datetime, timedelta

import jwt
from flask import current_app

from ..errors import Unauthorized

ACCESS = "access"
REFRESH = "refresh"


def create_token(user_id: int, token_type: str, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def issue_token_pair(user_id: int) -> dict:
    cfg = current_app.config
    return {
        "access_token": create_token(user_id, ACCESS, cfg["JWT_ACCESS_TTL"]),
        "refresh_token": create_token(user_id, REFRESH, cfg["JWT_REFRESH_TTL"]),
        "token_type": "Bearer",
        "expires_in": int(cfg["JWT_ACCESS_TTL"].total_seconds()),
    }


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"],  # always pin algorithms
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token has expired", code="token_expired")
    except jwt.InvalidTokenError:
        raise Unauthorized("Invalid token", code="token_invalid")
    if payload.get("type") != expected_type:
        raise Unauthorized("Wrong token type", code="token_invalid")
    return payload
