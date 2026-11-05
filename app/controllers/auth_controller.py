from flask import g, jsonify

from ..errors import Conflict, Unauthorized
from ..extensions import db
from ..models import User
from ..schemas import LoginSchema, RefreshSchema, RegisterSchema, user_out
from ..services.tokens import REFRESH, decode_token, issue_token_pair
from ..utils import get_json_body

# Used to burn equal CPU when the email doesn't exist -> blunts user-enumeration timing attacks.
_DUMMY = User(email="x@x.x", name="x")
_DUMMY.set_password("dummy-password")


def register():
    data = RegisterSchema().load(get_json_body())

    if db.session.scalar(db.select(User).where(User.email == data["email"])):
        raise Conflict("Email already registered", code="email_taken")

    user = User(email=data["email"], name=data["name"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()  # IntegrityError race -> handled globally as 409

    return jsonify({"user": user_out.dump(user), **issue_token_pair(user.id)}), 201


def login():
    data = LoginSchema().load(get_json_body())
    user = db.session.scalar(db.select(User).where(User.email == data["email"]))

    valid = (user or _DUMMY).check_password(data["password"]) and user is not None
    if not valid:
        raise Unauthorized("Invalid email or password", code="invalid_credentials")

    return jsonify({"user": user_out.dump(user), **issue_token_pair(user.id)}), 200


def refresh():
    data = RefreshSchema().load(get_json_body())
    payload = decode_token(data["refresh_token"], REFRESH)
    user = db.session.get(User, int(payload["sub"]))
    if user is None:
        raise Unauthorized("User no longer exists")
    return jsonify(issue_token_pair(user.id)), 200


def me():
    return jsonify({"user": user_out.dump(g.current_user)}), 200
