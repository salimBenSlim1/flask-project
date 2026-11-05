from flask import Blueprint

from ..controllers import auth_controller as c
from ..middleware.auth import login_required

auth_bp = Blueprint("auth", __name__)

auth_bp.post("/register")(c.register)
auth_bp.post("/login")(c.login)
auth_bp.post("/refresh")(c.refresh)
auth_bp.get("/me")(login_required(c.me))
