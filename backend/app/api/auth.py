from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import os
import time
from supabase import create_client
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Brute-force tracker: {email: {"count": int, "locked_until": float}}
_login_attempts: dict = {}
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


# ─── Token Helper ─────────────────────────────────────────────────
def create_token(user_id: str, role: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


# ─── Auth Dependency ──────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        return {"user_id": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ─── Brute-force helpers ──────────────────────────────────────────
def _check_lockout(email: str):
    entry = _login_attempts.get(email)
    if entry and entry["locked_until"] > time.monotonic():
        wait = int(entry["locked_until"] - time.monotonic())
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked. Try again in {wait} seconds.",
        )


def _record_failure(email: str):
    entry = _login_attempts.setdefault(email, {"count": 0, "locked_until": 0.0})
    entry["count"] += 1
    if entry["count"] >= _MAX_ATTEMPTS:
        entry["locked_until"] = time.monotonic() + _LOCKOUT_SECONDS
        entry["count"] = 0


def _clear_attempts(email: str):
    _login_attempts.pop(email, None)


# ─── Routes ───────────────────────────────────────────────────────
@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, req: SignupRequest):
    if req.role not in ["parent", "teacher"]:
        raise HTTPException(status_code=400, detail="Role must be 'parent' or 'teacher'")

    existing = supabase.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    domain = request.headers.get("X-Client-Domain", os.getenv("DEFAULT_CLIENT_DOMAIN", "threebabybirdies.com"))
    client = supabase.table("clients").select("id").eq(
        "domain", domain
    ).execute()
    client_id = client.data[0]["id"] if client.data else None

    hashed = pwd_context.hash(req.password)
    result = supabase.table("users").insert({
        "email": req.email,
        "password_hash": hashed,
        "role": req.role,
        "client_id": client_id,
        "subscription_status": "trial",
    }).execute()

    user = result.data[0]
    token = create_token(user["id"], user["role"])

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

    result = supabase.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        _record_failure(req.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]

    if not pwd_context.verify(req.password, user["password_hash"]):
        _record_failure(req.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _clear_attempts(req.email)
    token = create_token(user["id"], user["role"])

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
    result = supabase.table("users").select("*").eq(
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
