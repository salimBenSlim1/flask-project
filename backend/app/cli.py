"""CLI commands:  flask --app run seed"""
import click
from flask import current_app

from .extensions import db
from .models import Post, User

SEED_USERS = [
    {"email": "admin@example.com", "name": "Admin", "password": "Admin1234!", "role": "admin"},
    {"email": "alice@example.com", "name": "Alice", "password": "Alice1234!", "role": "user"},
    {"email": "bob@example.com", "name": "Bob", "password": "Bob12345!", "role": "user"},
]


def seed_demo_data() -> int:
    """Insert demo users/posts. Idempotent. Returns the number of newly created users."""
    created = 0
    for spec in SEED_USERS:
        user = db.session.scalar(db.select(User).where(User.email == spec["email"]))
        if user is None:
            user = User(email=spec["email"], name=spec["name"], role=spec["role"])
            user.set_password(spec["password"])
            db.session.add(user)
            db.session.flush()  # get user.id
            created += 1
        if not user.posts:
            db.session.add_all([
                Post(title=f"{user.name}'s first post", body="Hello from the seed script!", author_id=user.id),
                Post(title=f"{user.name} on Flask", body="Blueprints and app factories are neat.", author_id=user.id),
            ])
    db.session.commit()
    return created


def register_cli(app):
    @app.cli.command("seed")
    def seed():
        """Insert demo users and posts (idempotent). In production only if SEED_ON_START=true."""
        if current_app.config["APP_ENV"] == "production" and not current_app.config["SEED_ON_START"]:
            raise click.ClickException("Refusing to seed in production (set SEED_ON_START=true to allow)")

        created = seed_demo_data()
        click.echo(f"Seed done ({created} new users). Demo logins:")
        for u in SEED_USERS:
            click.echo(f"  {u['role']:<5} {u['email']:<20} {u['password']}")
