import io
import json

import pytest
from conftest import auth_header, make_pdf, upload
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

PAGES = [
    "The lease starts on 1 March and runs for twelve months.",
    "The monthly rent is 1200 euros, payable on the first day of each month.",
    "Pets are not allowed in the apartment without written permission.",
]


class FakeLLM:
    """Captures the rendered prompt and returns a canned answer."""

    def __init__(self):
        self.prompts = []

    def __call__(self):
        def run(prompt_value):
            self.prompts.append(prompt_value.to_string())
            return AIMessage(content="The rent is 1200 euros [1].")

        return RunnableLambda(run)


@pytest.fixture()
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr("app.controllers.document_controller.get_chat_model", fake)
    return fake


@pytest.fixture()
def alice(client):
    return auth_header(client)


@pytest.fixture()
def bob(client):
    return auth_header(client, email="bob@example.com", name="Bob")


def test_upload_ingests_and_lists(client, alice):
    res = upload(client, alice, PAGES)
    assert res.status_code == 202
    doc = res.get_json()["data"]
    assert doc["status"] == "ready" and doc["page_count"] == 3 and doc["chunk_count"] >= 3
    assert client.get("/api/documents", headers=alice).get_json()["data"][0]["id"] == doc["id"]


def test_rejects_non_pdf_and_missing_file(client, alice):
    res = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(b"hello"), "x.pdf")},
        headers=alice,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400 and res.get_json()["error"]["code"] == "invalid_file"
    res = client.post("/api/documents", headers=alice)
    assert res.get_json()["error"]["code"] == "file_required"


def test_pdf_without_text_fails_cleanly(client, alice):
    res = upload(client, alice, [""])
    doc = client.get(f"/api/documents/{res.get_json()['data']['id']}", headers=alice).get_json()["data"]
    assert doc["status"] == "failed" and "No text found" in doc["error"]


def test_corrupt_pdf_fails_cleanly(client, alice):
    broken = b"%PDF-1.4\nthis is not really a pdf"
    res = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(broken), "broken.pdf")},
        headers=alice,
        content_type="multipart/form-data",
    )
    doc = client.get(f"/api/documents/{res.get_json()['data']['id']}", headers=alice).get_json()["data"]
    assert doc["status"] == "failed" and doc["error"]


def test_ask_retrieves_the_right_page(client, alice, llm):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    res = client.post(
        f"/api/documents/{doc_id}/ask",
        json={"question": "How much is the monthly rent?", "stream": False},
        headers=alice,
    )
    body = res.get_json()["data"]
    assert res.status_code == 200 and "1200" in body["answer"]
    assert body["sources"][0]["page"] == 2  # best match is the rent page
    assert "monthly rent is 1200" in llm.prompts[0]


def test_ask_streams_sse(client, alice, llm):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    res = client.post(f"/api/documents/{doc_id}/ask", json={"question": "rent?"}, headers=alice)
    assert res.mimetype == "text/event-stream"
    events = [e for e in res.get_data(as_text=True).strip().split("\n\n")]
    names = [e.splitlines()[0] for e in events]
    assert names[0] == "event: sources" and names[-1] == "event: done" and "event: token" in names
    token = next(e for e in events if e.startswith("event: token"))
    assert "rent" in json.loads(token.splitlines()[1][len("data: "):])["text"]


def test_history_is_passed_to_the_model(client, alice, llm):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    history = [{"role": "user", "content": "Tell me about pets"}, {"role": "assistant", "content": "Not allowed."}]
    client.post(
        f"/api/documents/{doc_id}/ask",
        json={"question": "And rent?", "history": history, "stream": False},
        headers=alice,
    )
    assert "Tell me about pets" in llm.prompts[0] and "Not allowed." in llm.prompts[0]


def test_users_cannot_touch_each_others_documents(client, alice, bob, llm):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    assert client.get(f"/api/documents/{doc_id}", headers=bob).status_code == 404
    assert client.post(f"/api/documents/{doc_id}/ask", json={"question": "rent?"}, headers=bob).status_code == 404
    assert client.delete(f"/api/documents/{doc_id}", headers=bob).status_code == 404
    assert client.get("/api/documents", headers=bob).get_json()["data"] == []


def test_retrieval_never_crosses_users(client, alice, bob, llm):
    upload(client, alice, ["Alice secret: the vault code is 4821."])
    bob_doc = upload(client, bob, ["Bob notes about gardening and tomatoes."]).get_json()["data"]["id"]
    client.post(
        f"/api/documents/{bob_doc}/ask",
        json={"question": "What is the vault code?", "stream": False},
        headers=bob,
    )
    assert "4821" not in llm.prompts[0]


def test_delete_removes_document_and_chunks(client, app, alice):
    from app.extensions import db
    from app.models import Chunk

    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    assert client.delete(f"/api/documents/{doc_id}", headers=alice).status_code == 204
    assert client.get(f"/api/documents/{doc_id}", headers=alice).status_code == 404
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Chunk.id))) == 0


def test_question_validation(client, alice, llm):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    res = client.post(f"/api/documents/{doc_id}/ask", json={"question": "   "}, headers=alice)
    assert res.status_code == 422 and "question" in res.get_json()["error"]["details"]


def test_document_quota(client, app, alice):
    app.config["MAX_DOCS_PER_USER"] = 1
    assert upload(client, alice, PAGES).status_code == 202
    res = upload(client, alice, PAGES)
    assert res.status_code == 403 and res.get_json()["error"]["code"] == "quota_exceeded"


def test_missing_api_key_is_a_clear_503(client, app, alice):
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    app.config["ANTHROPIC_API_KEY"] = None
    res = client.post(f"/api/documents/{doc_id}/ask", json={"question": "rent?"}, headers=alice)
    assert res.status_code == 503 and res.get_json()["error"]["code"] == "llm_not_configured"

def test_chat_model_uses_groq_with_existing_render_settings(app, monkeypatch):
    from app.services.rag import chain

    captured = {}

    class FakeChatGroq:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(chain, "ChatGroq", FakeChatGroq)
    app.config["ANTHROPIC_API_KEY"] = "groq-test-key"
    app.config["ANTHROPIC_MODEL"] = "openai/gpt-oss-20b"

    with app.app_context():
        model = chain.get_chat_model()

    assert isinstance(model, FakeChatGroq)
    assert captured["api_key"] == "groq-test-key"
    assert captured["model"] == "openai/gpt-oss-20b"


def test_llm_failure_is_a_502_not_a_stack_trace(client, alice, monkeypatch):
    def boom(_):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr("app.controllers.document_controller.get_chat_model", lambda: RunnableLambda(boom))
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    res = client.post(f"/api/documents/{doc_id}/ask", json={"question": "rent?", "stream": False}, headers=alice)
    assert res.status_code == 502 and "exploded" not in res.get_data(as_text=True)


def test_rate_limit(client, app, alice, llm):
    class FakeRedis:
        def __init__(self):
            self.n = 0

        def incr(self, key):
            self.n += 1
            return self.n

        def expire(self, key, seconds):
            pass

    app.extensions["redis"] = FakeRedis()
    app.config["ASK_RATE_LIMIT"] = 2
    doc_id = upload(client, alice, PAGES).get_json()["data"]["id"]
    codes = [
        client.post(f"/api/documents/{doc_id}/ask", json={"question": "rent?", "stream": False}, headers=alice).status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 429]


def test_oversized_upload_is_a_json_413(client, app, alice):
    app.config["MAX_CONTENT_LENGTH"] = 1000
    res = upload(client, alice, ["x " * 2000])
    assert res.status_code == 413 and res.get_json()["error"]["code"] == "request_entity_too_large"


def test_pdf_builder_roundtrip():
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(make_pdf(["hello (world)"])))
    assert "hello (world)" in reader.pages[0].extract_text()
