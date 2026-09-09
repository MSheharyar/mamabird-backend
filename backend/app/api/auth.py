from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
import secrets

from app.limiter import limiter
from app.db.client import get_supabase
from app.services import mailer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(hours=24)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300

# Password rules. Signup accepted anything at all — including a single
# character — while the sign-up form promised "at least 8 characters".
MIN_PASSWORD_LEN = 8

RESET_TTL_MINUTES = 60
_RESET_MAX_PER_HOUR = 3          # per account, on top of the per-IP limiter
SITE_URL = os.getenv("SITE_URL", "https://threebabybirdies.com")


# ─── Request Models ───────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    password: str


# ─── Token Helpers ─────────────────────────────────────────────────
def create_token(
    user_id: str,
    role: str,
    client_id: str = None,
    token_version: int = 0,
) -> str:
    expire = datetime.now(timezone.utc) + ACCESS_TTL
    payload: dict = {
        "sub": user_id,
        "role": role,
        "ver": token_version,
        "exp": expire,
    }
    if client_id:
        payload["client_id"] = client_id
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def revoke_all(user_id: str) -> None:
    """Increment token_version, immediately invalidating all live tokens for this user."""
    row = get_supabase().table("users").select("token_version").eq("id", user_id).execute()
    if not row.data:
        return
    new_ver = (row.data[0].get("token_version") or 0) + 1
    get_supabase().table("users").update({"token_version": new_ver}).eq("id", user_id).execute()


# ─── Auth Dependency ──────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    claimed_ver = payload.get("ver", 0)

    # Revocation check: token_version must match the DB record
    # One read of the user row, not three. require_subscription and the chat
    # endpoint both re-queried this same row for subscription fields, costing
    # two extra Supabase round trips on every authenticated request.
    result = get_supabase().table("users").select(
        "role, client_id, token_version, subscription_status, trial_ends_at, subscription_plan"
    ).eq("id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = result.data[0]
    if user.get("token_version", 0) != claimed_ver:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "user_id": user_id,
        "role": user.get("role", payload.get("role")),
        "client_id": user.get("client_id") or payload.get("client_id"),
        # Carried so downstream dependencies do not re-fetch the same row.
        "subscription_status": user.get("subscription_status"),
        "trial_ends_at": user.get("trial_ends_at"),
        "subscription_plan": user.get("subscription_plan"),
    }


# ─── Brute-force Helpers ──────────────────────────────────────────
def _check_lockout(email: str) -> None:
    result = get_supabase().table("login_attempts").select("locked_until").eq("email", email).execute()
    if not result.data:
        return
    locked_until_raw = result.data[0].get("locked_until")
    if not locked_until_raw:
        return
    locked_until = datetime.fromisoformat(locked_until_raw.replace("Z", "+00:00"))
    if locked_until > datetime.now(timezone.utc):
        wait = int((locked_until - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked. Try again in {wait} seconds.",
        )


def _record_failure(email: str) -> None:
    get_supabase().rpc("record_login_failure", {
        "p_email": email,
        "p_max_attempts": _MAX_ATTEMPTS,
        "p_lockout_seconds": _LOCKOUT_SECONDS,
    }).execute()


def _clear_attempts(email: str) -> None:
    get_supabase().table("login_attempts").delete().eq("email", email).execute()


# ─── Routes ───────────────────────────────────────────────────────
@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, req: SignupRequest):
    if req.role not in ["parent", "teacher"]:
        raise HTTPException(status_code=400, detail="Role must be 'parent' or 'teacher'")

    if len(req.password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LEN} characters",
        )

    sb = get_supabase()
    # Login already answers "Invalid email or password" for both cases, but
    # signup answered "Email already registered", which turns this endpoint
    # into an oracle for whether any given address has an account.
    existing = sb.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=400,
            detail="We could not create that account. If you already have one, try signing in.",
        )

    domain = request.headers.get(
        "X-Client-Domain",
        os.getenv("DEFAULT_CLIENT_DOMAIN", "threebabybirdies.com"),
    )
    client = sb.table("clients").select("id").eq("domain", domain).execute()
    client_id = client.data[0]["id"] if client.data else None

    hashed = pwd_context.hash(req.password)
    result = sb.table("users").insert({
        "email": req.email,
        "password_hash": hashed,
        "role": req.role,
        "client_id": client_id,
        "subscription_status": "trial",
    }).execute()

    user = result.data[0]
    token = create_token(
        user["id"],
        user["role"],
        client_id,
        user.get("token_version", 0),
    )

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "subscription_status": user["subscription_status"],
            "trial_ends_at": user["trial_ends_at"],
        },
    }


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest):
    _check_lockout(req.email)

    sb = get_supabase()
    result = sb.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        _record_failure(req.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]

    if not pwd_context.verify(req.password, user["password_hash"]):
        _record_failure(req.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _clear_attempts(req.email)
    token = create_token(
        user["id"],
        user["role"],
        user.get("client_id"),
        user.get("token_version", 0),
    )

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "subscription_status": user["subscription_status"],
            "trial_ends_at": user["trial_ends_at"],
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    result = get_supabase().table("users").select("*").eq(
        "id", current_user["user_id"]
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data[0]
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "subscription_status": user["subscription_status"],
        "trial_ends_at": user["trial_ends_at"],
    }


@router.post("/delete-account")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """
    Permanently delete the signed-in account and all associated data.

    Required by the Apple App Store (in-app account deletion) and Google Play,
    and by our COPPA commitment that a parent can erase their child's data on
    request. This wipes the user, every child profile they own, and all rows
    that reference those children.
    """
    sb = get_supabase()
    user_id = current_user["user_id"]

    row = sb.table("users").select("email").eq("id", user_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="User not found")
    email = row.data[0].get("email")

    # Child profiles owned by this user, and every table that references them.
    child_rows = sb.table("child_profiles").select("id").eq("user_id", user_id).execute()
    child_ids = [c["id"] for c in (child_rows.data or [])]

    child_tables = ("progress", "badges", "chat_sessions",
                    "message_counts", "usage_logs", "lesson_plans")
    for cid in child_ids:
        for tbl in child_tables:
            try:
                sb.table(tbl).delete().eq("child_profile_id", cid).execute()
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                logger.warning("delete_account: cleanup of %s failed: %s", tbl, exc)

    # User-scoped rows.
    for tbl in ("child_profiles", "classrooms", "lesson_plans"):
        try:
            sb.table(tbl).delete().eq("user_id", user_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("delete_account: cleanup of %s (user) failed: %s", tbl, exc)

    if email:
        try:
            sb.table("login_attempts").delete().eq("email", email).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("delete_account: login_attempts cleanup failed: %s", exc)

    # NOTE: if the user has a live Stripe subscription, cancel it in Stripe
    # before/after this call (stripe_customer_id lives on the user row).
    sb.table("users").delete().eq("id", user_id).execute()

    return {"message": "Account deleted"}


# ─── Password reset ───────────────────────────────────────────────
def _hash_token(token: str) -> str:
    """Only the hash is ever stored, so a dump of the table is not usable."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request, req: ForgotPasswordRequest):
    """
    Always answers the same thing. Whether the address exists, whether SMTP
    is configured, and whether the send succeeded are all invisible to the
    caller — otherwise this endpoint tells an attacker which addresses have
    accounts, which is exactly what login and signup are careful not to do.
    """
    same_answer = {
        "message": "If that address has an account, a reset link is on its way."
    }
    email = req.email.strip().lower()
    sb = get_supabase()

    try:
        found = sb.table("users").select("id").eq("email", email).execute()
        if not found.data:
            return same_answer
        user_id = found.data[0]["id"]

        # Per-account throttle, so knowing an address is not enough to bury
        # someone in mail. The IP limiter above handles the spray case.
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        recent = sb.table("password_resets").select("id").eq(
            "user_id", user_id
        ).gte("created_at", since).execute()
        if recent.data and len(recent.data) >= _RESET_MAX_PER_HOUR:
            logger.warning("Password reset throttled for user %s", user_id)
            return same_answer

        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TTL_MINUTES)
        sb.table("password_resets").insert({
            "user_id": user_id,
            "token_hash": _hash_token(token),
            "expires_at": expires.isoformat(),
            "requested_ip": (request.client.host if request.client else None),
        }).execute()

        url = f"{SITE_URL}/reset-password.html?token={token}"
        subject, text, html = mailer.password_reset_email(url, RESET_TTL_MINUTES)
        mailer.send(email, subject, text, html)
    except Exception:
        logger.exception("forgot_password failed")

    return same_answer


@router.post("/reset-password")
@limiter.limit("10/hour")
async def reset_password(request: Request, req: ResetPasswordRequest):
    if len(req.password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LEN} characters",
        )

    sb = get_supabase()
    rows = sb.table("password_resets").select("*").eq(
        "token_hash", _hash_token(req.token)
    ).execute()

    invalid = HTTPException(
        status_code=400,
        detail="That reset link is invalid or has expired. Please request a new one.",
    )
    if not rows.data:
        raise invalid

    row = rows.data[0]
    if row.get("used_at"):
        raise invalid
    try:
        expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    except (ValueError, TypeError, KeyError):
        raise invalid
    if datetime.now(timezone.utc) > expires:
        raise invalid

    user_id = row["user_id"]
    sb.table("users").update(
        {"password_hash": pwd_context.hash(req.password)}
    ).eq("id", user_id).execute()

    # Single use, and any other outstanding link for this account dies too.
    now = datetime.now(timezone.utc).isoformat()
    sb.table("password_resets").update({"used_at": now}).eq("id", row["id"]).execute()
    sb.table("password_resets").update({"used_at": now}).eq(
        "user_id", user_id
    ).is_("used_at", "null").execute()

    # Whoever changed the password keeps their new session; every other live
    # token for this account stops working. If the reset was a recovery from
    # a compromise, the attacker is logged out by this line.
    revoke_all(user_id)

    # A successful reset should not leave the account still locked out from
    # the failed attempts that led here.
    try:
        user = sb.table("users").select("email").eq("id", user_id).execute()
        if user.data:
            sb.table("login_attempts").delete().eq(
                "email", user.data[0]["email"]
            ).execute()
    except Exception:
        logger.warning("reset_password: could not clear login_attempts", exc_info=True)

    logger.info("Password reset completed for user %s", user_id)
    return {"message": "Your password has been changed. You can sign in with it now."}
