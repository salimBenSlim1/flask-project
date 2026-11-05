from flask import g, jsonify, request

from ..errors import Forbidden, NotFound
from ..extensions import db
from ..models import Post
from ..models.user import ROLE_ADMIN
from ..schemas import PostCreateSchema, post_out, posts_out
from ..utils import get_json_body


def _get_post_or_404(post_id: int) -> Post:
    post = db.session.get(Post, post_id)
    if post is None:
        raise NotFound("Post not found")
    return post


def _assert_can_modify(post: Post) -> None:
    user = g.current_user
    if post.author_id != user.id and user.role != ROLE_ADMIN:
        raise Forbidden("You can only modify your own posts")


def list_posts():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)

    pagination = db.paginate(
        db.select(Post).order_by(Post.created_at.desc(), Post.id.desc()),
        page=page, per_page=per_page, error_out=False,
    )
    return jsonify({
        "data": posts_out.dump(pagination.items),
        "meta": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        },
    }), 200


def get_post(post_id: int):
    return jsonify({"data": post_out.dump(_get_post_or_404(post_id))}), 200


def create_post():
    data = PostCreateSchema().load(get_json_body())
    post = Post(**data, author_id=g.current_user.id)
    db.session.add(post)
    db.session.commit()
    return jsonify({"data": post_out.dump(post)}), 201


def update_post(post_id: int):
    post = _get_post_or_404(post_id)
    _assert_can_modify(post)

    data = PostCreateSchema().load(get_json_body(), partial=True)  # PATCH semantics
    for field, value in data.items():
        setattr(post, field, value)
    db.session.commit()
    return jsonify({"data": post_out.dump(post)}), 200


def delete_post(post_id: int):
    post = _get_post_or_404(post_id)
    _assert_can_modify(post)
    db.session.delete(post)
    db.session.commit()
    return "", 204
