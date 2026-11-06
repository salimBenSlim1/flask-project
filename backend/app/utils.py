from flask import request

from .errors import BadRequest


def get_json_body() -> dict:
    """Parse JSON safely. `silent=True` avoids Flask's default HTML 400/415 page."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object")
    return data
