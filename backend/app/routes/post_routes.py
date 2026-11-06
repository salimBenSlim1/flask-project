from flask import Blueprint

from ..controllers import post_controller as c
from ..middleware.auth import login_required

posts_bp = Blueprint("posts", __name__)

posts_bp.get("")(c.list_posts)                              # public
posts_bp.get("/<int:post_id>")(c.get_post)                  # public
posts_bp.post("")(login_required(c.create_post))
posts_bp.patch("/<int:post_id>")(login_required(c.update_post))
posts_bp.delete("/<int:post_id>")(login_required(c.delete_post))
