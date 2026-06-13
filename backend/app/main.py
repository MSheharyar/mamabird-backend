import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.limiter import limiter
from app.api import auth, profiles, config_test, chat, lesson_plans, badges, sessions, dashboard

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REQUIRED_ENV = [
    "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "JWT_SECRET", "ANTHROPIC_API_KEY",
]

app = FastAPI(title="MamaBird Chatbot API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def validate_env():
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.monotonic()

    request.state.request_id = request_id
    logger.info("REQ %s %s %s", request_id, request.method, request.url.path)

    response = await call_next(request)

    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    logger.info(
        "RES %s %s %s %dms",
        request_id,
        request.method,
        request.url.path,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled error [%s]: %s", request_id, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(config_test.router)
app.include_router(chat.router)
app.include_router(lesson_plans.router)
app.include_router(badges.router)
app.include_router(sessions.router)
app.include_router(dashboard.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MamaBird API is running 🐦"}
