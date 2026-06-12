from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from supabase import create_client

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Request Models ───────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    role: str  # "parent" or "teacher"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ─── Token Helper ─────────────────────────────────────────────────
def create_token(user_id: str, role: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

# ─── Auth Dependency (used by other routes) ───────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return {"user_id": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ─── Routes ───────────────────────────────────────────────────────
@router.post("/signup")
async def signup(req: SignupRequest):
    if req.role not in ["parent", "teacher"]:
        raise HTTPException(status_code=400, detail="Role must be 'parent' or 'teacher'")

    # Check if email already exists
    existing = supabase.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Get the client_id for threebabybirdies.com
    client = supabase.table("clients").select("id").eq(
        "domain", "threebabybirdies.com"
    ).execute()
    client_id = client.data[0]["id"] if client.data else None

    # Hash password and create user
    hashed = pwd_context.hash(req.password)
    result = supabase.table("users").insert({
        "email": req.email,
        "password_hash": hashed,
        "role": req.role,
        "client_id": client_id,
        "subscription_status": "trial"
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
            "trial_ends_at": user["trial_ends_at"]
        }
    }

@router.post("/login")
async def login(req: LoginRequest):
    # Find user by email
    result = supabase.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]

    # Check password
    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["role"])

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "subscription_status": user["subscription_status"],
            "trial_ends_at": user["trial_ends_at"]
        }
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
        "trial_ends_at": user["trial_ends_at"]
    }