"""Marshmallow = Joi/Zod + serializer. `load()` validates input, `dump()` shapes output."""
from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_load, validate


def strong_password(value: str) -> None:
    if not (any(c.isalpha() for c in value) and any(c.isdigit() for c in value)):
        raise ValidationError("Password must contain at least one letter and one number.")


class _Base(Schema):
    class Meta:
        unknown = EXCLUDE  # silently drop unknown keys (mass-assignment protection)


class RegisterSchema(_Base):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=[validate.Length(min=8, max=128), strong_password],
    )

    @post_load
    def normalize(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        data["name"] = data["name"].strip()
        return data


class LoginSchema(_Base):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

    @post_load
    def normalize(self, data, **kwargs):
        data["email"] = data["email"].strip().lower()
        return data


class RefreshSchema(_Base):
    refresh_token = fields.Str(required=True)


class PostCreateSchema(_Base):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    body = fields.Str(required=True, validate=validate.Length(min=1))


class HistoryItemSchema(_Base):
    role = fields.Str(required=True, validate=validate.OneOf(["user", "assistant"]))
    content = fields.Str(required=True, validate=validate.Length(min=1, max=4000))


class AskSchema(_Base):
    question = fields.Str(
        required=True,
        validate=[validate.Length(max=1000), validate.Regexp(r"\S", error="Question can't be empty.")],
    )
    history = fields.List(
        fields.Nested(HistoryItemSchema), load_default=list, validate=validate.Length(max=6)
    )
    stream = fields.Bool(load_default=True)

    @post_load
    def normalize(self, data, **kwargs):
        data["question"] = data["question"].strip()
        return data


class DocumentOutSchema(_Base):
    id = fields.Int()
    filename = fields.Str()
    size_bytes = fields.Int()
    status = fields.Str()
    error = fields.Str(allow_none=True)
    page_count = fields.Int(allow_none=True)
    chunk_count = fields.Int(allow_none=True)
    created_at = fields.DateTime()


class UserOutSchema(_Base):
    id = fields.Int()
    name = fields.Str()
    email = fields.Str()
    role = fields.Str()
    created_at = fields.DateTime()


class PostOutSchema(_Base):
    id = fields.Int()
    title = fields.Str()
    body = fields.Str()
    author = fields.Nested(UserOutSchema(only=("id", "name")))
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


user_out = UserOutSchema()
post_out = PostOutSchema()
posts_out = PostOutSchema(many=True)

document_out = DocumentOutSchema()
documents_out = DocumentOutSchema(many=True)
