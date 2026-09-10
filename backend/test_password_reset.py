"""Tests for the password reset flow. No running server or real DB.

The things worth proving here are the security properties, not the happy
path: that the raw token never reaches the database, that a link works
once, that an expired one is refused, and that the endpoint says the same
thing whether or not the address exists.
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import auth  # noqa: E402
from app.main import app  # noqa: E402

USER_ID = "11111111-2222-3333-4444-555555555555"
EMAIL = "parent@example.com"


class _Res:
    def __init__(self, data):
        self.data = data


class _Table:
    """Enough of the supabase-py builder to drive these two endpoints."""

    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.pending, self.op = {}, None, None

    # -- builder ------------------------------------------------------
    def select(self, *_a, **_kw):
        self.op = "select"; return self

    def insert(self, row, **_kw):
        self.op = "insert"; self.pending = row; return self

    def update(self, patch, **_kw):
        self.op = "update"; self.pending = patch; return self

    def delete(self, **_kw):
        self.op = "delete"; return self

    def eq(self, col, val):
        self.filters[col] = val; return self

    def gte(self, col, val):
        self.filters["__gte__" + col] = val; return self

    def is_(self, col, _val):
        self.filters["__isnull__" + col] = True; return self

    # -- execution ----------------------------------------------------
    def _match(self, row):
        for k, v in self.filters.items():
            if k.startswith("__gte__"):
                if row.get(k[7:], "") < v:
                    return False
            elif k.startswith("__isnull__"):
                if row.get(k[10:]) is not None:
                    return False
            elif row.get(k) != v:
                return False
        return True

    def execute(self):
        rows = self.db.setdefault(self.name, [])
        if self.op == "insert":
            row = dict(self.pending)
            row.setdefault("id", "row-%d" % (len(rows) + 1))
            row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            row.setdefault("used_at", None)
            rows.append(row)
            return _Res([row])
        hits = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hits:
                r.update(self.pending)
        elif self.op == "delete":
            for r in hits:
                rows.remove(r)
        return _Res(hits)


class _Fake:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return _Table(self.db, name)


def _install(monkeypatch, resets=None):
    db = {
        "users": [{"id": USER_ID, "email": EMAIL, "password_hash": "old", "token_version": 3}],
        "password_resets": list(resets or []),
        "login_attempts": [{"email": EMAIL, "attempts": 5}],
    }
    fake = _Fake(db)
    monkeypatch.setattr(auth, "get_supabase", lambda: fake)
    sent = []
    monkeypatch.setattr(auth.mailer, "send",
                        lambda to, s, t, h=None: sent.append({"to": to, "text": t}) or True)
    return db, sent


def _row(token, *, minutes=60, used=False):
    return {
        "id": "r1", "user_id": USER_ID,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(),
        "used_at": datetime.now(timezone.utc).isoformat() if used else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


SAME = "If that address has an account, a reset link is on its way."


# ── request ───────────────────────────────────────────────────────────
def test_unknown_address_is_indistinguishable(monkeypatch):
    db, sent = _install(monkeypatch)
    with TestClient(app) as c:
        res = c.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert res.status_code == 200
    assert res.json()["message"] == SAME
    assert db["password_resets"] == [], "must not create a token for an unknown address"
    assert sent == [], "must not send mail to an address with no account"
    print("forgot: unknown address gets the same answer and creates nothing OK")


def test_known_address_stores_only_a_hash(monkeypatch):
    db, sent = _install(monkeypatch)
    with TestClient(app) as c:
        res = c.post("/auth/forgot-password", json={"email": EMAIL})
    assert res.json()["message"] == SAME, "answer must not differ from the unknown case"
    assert len(db["password_resets"]) == 1
    row = db["password_resets"][0]
    assert len(row["token_hash"]) == 64, "should be a sha256 hex digest"
    assert "token" not in row, "the raw token must never be a column"
    assert len(sent) == 1 and sent[0]["to"] == EMAIL
    # the link in the mail must not be the value we stored
    assert row["token_hash"] not in sent[0]["text"]
    print("forgot: stores sha256 only, mails the raw token OK")


def test_repeat_requests_are_throttled_per_account(monkeypatch):
    existing = [_row("t%d" % i) for i in range(auth._RESET_MAX_PER_HOUR)]
    db, sent = _install(monkeypatch, resets=existing)
    with TestClient(app) as c:
        res = c.post("/auth/forgot-password", json={"email": EMAIL})
    assert res.json()["message"] == SAME, "throttling must be invisible to the caller"
    assert len(db["password_resets"]) == auth._RESET_MAX_PER_HOUR, "no extra token"
    assert sent == [], "no extra mail"
    print("forgot: throttled after %d in an hour, silently OK" % auth._RESET_MAX_PER_HOUR)


# ── consume ───────────────────────────────────────────────────────────
def test_valid_token_changes_password_and_kills_sessions(monkeypatch):
    db, _ = _install(monkeypatch, resets=[_row("good-token-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")])
    with TestClient(app) as c:
        res = c.post("/auth/reset-password",
                     json={"token": "good-token-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "password": "a-good-password"})
    assert res.status_code == 200, res.text
    user = db["users"][0]
    assert user["password_hash"] != "old"
    assert user["token_version"] == 4, "every other live session must be revoked"
    assert db["password_resets"][0]["used_at"] is not None, "token must be single use"
    assert db["login_attempts"] == [], "lockout from the failed attempts must be cleared"
    print("reset: password changed, sessions revoked, lockout cleared OK")


def test_token_cannot_be_reused(monkeypatch):
    db, _ = _install(monkeypatch, resets=[_row("used-token-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", used=True)])
    with TestClient(app) as c:
        res = c.post("/auth/reset-password",
                     json={"token": "used-token-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "password": "another-password"})
    assert res.status_code == 400
    assert db["users"][0]["password_hash"] == "old"
    print("reset: a spent link is refused OK")


def test_expired_token_is_refused(monkeypatch):
    db, _ = _install(monkeypatch, resets=[_row("stale-token-cccccccccccccccccccccccccccccc", minutes=-1)])
    with TestClient(app) as c:
        res = c.post("/auth/reset-password",
                     json={"token": "stale-token-cccccccccccccccccccccccccccccc", "password": "another-password"})
    assert res.status_code == 400
    assert db["users"][0]["password_hash"] == "old"
    print("reset: an expired link is refused OK")


def test_unknown_token_is_refused(monkeypatch):
    db, _ = _install(monkeypatch, resets=[_row("real-token-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")])
    with TestClient(app) as c:
        res = c.post("/auth/reset-password",
                     json={"token": "guessed-token-dddddddddddddddddddddddddddd", "password": "another-password"})
    assert res.status_code == 400
    assert db["users"][0]["password_hash"] == "old"
    print("reset: an unknown token is refused OK")


def test_short_password_is_refused(monkeypatch):
    db, _ = _install(monkeypatch, resets=[_row("good-token-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")])
    with TestClient(app) as c:
        res = c.post("/auth/reset-password", json={"token": "good-token-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "password": "short"})
    assert res.status_code == 400
    assert db["users"][0]["password_hash"] == "old"
    assert db["password_resets"][0]["used_at"] is None, "a rejected attempt must not burn the link"
    print("reset: password under %d characters refused, link survives OK" % auth.MIN_PASSWORD_LEN)


def test_signup_enforces_the_same_minimum(monkeypatch):
    _install(monkeypatch)
    with TestClient(app) as c:
        res = c.post("/auth/signup", json={"email": "new@example.com",
                                           "password": "tiny", "role": "parent"})
    assert res.status_code == 400
    assert "8 characters" in res.json()["detail"]
    print("signup: rejects a password under %d characters OK" % auth.MIN_PASSWORD_LEN)
