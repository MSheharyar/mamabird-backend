"""Tests for the public newsletter endpoint. No running server or real DB."""
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import leads  # noqa: E402
from app.main import app  # noqa: E402


CLIENT_ID = "11111111-2222-3333-4444-555555555555"


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """Records what the endpoint asked for, and replays canned rows."""

    def __init__(self, store, name):
        self._store = store
        self._name = name
        self._filters = {}
        self._pending_insert = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def insert(self, row, **_kw):
        # supabase-py returns a builder here; the caller then calls .execute().
        self._pending_insert = row
        return self

    def execute(self):
        if self._pending_insert is not None:
            row = self._pending_insert
            self._pending_insert = None
            self._store["inserted"].append(row)
            return _Result([row])
        if self._name == "clients":
            return _Result([{"id": CLIENT_ID}] if self._store["client_exists"] else [])
        if self._filters.get("email") in self._store["existing_emails"]:
            return _Result([{"id": "existing-lead"}])
        return _Result([])


class _FakeSupabase:
    def __init__(self, store):
        self._store = store

    def table(self, name):
        return _FakeTable(self._store, name)


def _install(monkeypatch, *, existing=(), client_exists=True):
    store = {
        "inserted": [],
        "existing_emails": set(existing),
        "client_exists": client_exists,
    }
    fake = _FakeSupabase(store)
    monkeypatch.setattr(leads, "get_supabase", lambda: fake)
    return store


def _post(client, **body):
    payload = {"email": "parent@example.com", "source": "homepage_newsletter"}
    payload.update(body)
    return client.post("/leads/subscribe", json=payload)


def test_subscribe_stores_lead_against_the_client(monkeypatch):
    store = _install(monkeypatch)
    with TestClient(app) as client:
        res = _post(client, first_name="Iris")

    assert res.status_code == 200, res.text
    assert res.json() == {"status": "subscribed"}
    assert len(store["inserted"]) == 1
    row = store["inserted"][0]
    assert row["email"] == "parent@example.com"
    assert row["first_name"] == "Iris"
    assert row["source"] == "homepage_newsletter"
    assert row["client_id"] == CLIENT_ID, "TenantSafeQuery must stamp client_id"
    print("subscribe: stores the lead with client_id OK")


def test_email_is_normalised(monkeypatch):
    store = _install(monkeypatch)
    with TestClient(app) as client:
        res = _post(client, email="  Parent@Example.COM  ")

    assert res.status_code == 200, res.text
    assert store["inserted"][0]["email"] == "parent@example.com"
    print("subscribe: trims and lowercases the address OK")


def test_resubscribe_is_a_silent_no_op(monkeypatch):
    store = _install(monkeypatch, existing={"parent@example.com"})
    with TestClient(app) as client:
        res = _post(client)

    assert res.status_code == 200, res.text
    assert res.json() == {"status": "subscribed"}, "must not reveal prior membership"
    assert store["inserted"] == [], "must not write a duplicate row"
    print("subscribe: re-subscribing does not duplicate or leak OK")


def test_unknown_source_is_not_stored_verbatim(monkeypatch):
    store = _install(monkeypatch)
    with TestClient(app) as client:
        res = _post(client, source="<script>alert(1)</script>")

    assert res.status_code == 200, res.text
    assert store["inserted"][0]["source"] == "unknown"
    print("subscribe: unrecognised source falls back to 'unknown' OK")


def test_invalid_email_is_rejected(monkeypatch):
    store = _install(monkeypatch)
    with TestClient(app) as client:
        res = _post(client, email="not-an-address")

    assert res.status_code == 422
    assert store["inserted"] == []
    print("subscribe: invalid address rejected before any write OK")


def test_missing_client_row_does_not_leak_internals(monkeypatch):
    _install(monkeypatch, client_exists=False)
    with TestClient(app) as client:
        res = _post(client)

    assert res.status_code == 500
    assert "Traceback" not in res.text
    assert res.json()["detail"] == "Client configuration not found"
    print("subscribe: missing client row returns a clean 500 OK")
