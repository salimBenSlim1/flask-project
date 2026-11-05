from conftest import auth_header, register


def test_register_login_me(client):
    assert register(client).status_code == 201
    res = client.post("/api/auth/login", json={"email": "A@example.com", "password": "supersecret1"})
    assert res.status_code == 200
    token = res.get_json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.get_json()["user"]["email"] == "a@example.com"
    assert "password" not in str(me.get_json())


def test_duplicate_email_conflict(client):
    register(client)
    res = register(client)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "email_taken"


def test_validation_error_shape(client):
    res = client.post("/api/auth/register", json={"email": "nope", "password": "x"})
    body = res.get_json()["error"]
    assert res.status_code == 422 and body["code"] == "validation_error"
    assert {"email", "password", "name"} <= set(body["details"])


def test_bad_json_and_404_are_json(client):
    assert client.post("/api/auth/login", data="not json", content_type="application/json").status_code == 400
    res = client.get("/nope")
    assert res.status_code == 404 and res.get_json()["error"]["code"] == "not_found"


def test_auth_required_and_bad_token(client):
    assert client.post("/api/posts", json={"title": "t", "body": "b"}).status_code == 401
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert res.status_code == 401 and res.get_json()["error"]["code"] == "token_invalid"


def test_refresh_token_cannot_be_used_as_access(client):
    refresh = register(client).get_json()["refresh_token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert res.status_code == 401


def test_post_crud_and_ownership(client):
    alice = auth_header(client)
    bob = auth_header(client, email="b@example.com", name="Bob")

    created = client.post("/api/posts", json={"title": "Hi", "body": "World"}, headers=alice)
    assert created.status_code == 201
    pid = created.get_json()["data"]["id"]

    assert client.patch(f"/api/posts/{pid}", json={"title": "X"}, headers=bob).status_code == 403
    upd = client.patch(f"/api/posts/{pid}", json={"title": "New"}, headers=alice)
    assert upd.get_json()["data"]["title"] == "New"

    listing = client.get("/api/posts?per_page=5").get_json()
    assert listing["meta"]["total"] == 1

    assert client.delete(f"/api/posts/{pid}", headers=alice).status_code == 204
    assert client.get(f"/api/posts/{pid}").status_code == 404


def test_weak_password_rejected(client):
    res = register(client, password="onlyletters")
    assert res.status_code == 422
    assert "number" in res.get_json()["error"]["details"]["password"][0]
