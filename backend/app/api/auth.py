from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import os

from app.limiter import limiter
from app.db.client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(hours=24)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300


# ─── Request Models ───────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
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
    result = get_supabase().table("users").select(
        "role, client_id, token_version"
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

    sb = get_supabase()
    existing = sb.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

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
