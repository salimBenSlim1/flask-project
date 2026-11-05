import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="a@example.com", name="Alice", password="supersecret1"):
    res = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    return res


def auth_header(client, **kw):
    token = register(client, **kw).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
