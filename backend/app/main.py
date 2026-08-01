import logging
import time
import uuid
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.limiter import limiter
from app.api import auth, profiles, config_test, chat, lesson_plans, badges, sessions, dashboard, admin, payments, classrooms, demo_business

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REQUIRED_ENV = [
    "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "JWT_SECRET", "ANTHROPIC_API_KEY",
]

# Sentry — only initialises when SENTRY_DSN is set (safe to omit in dev)
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )

_docs_url = "/docs" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None
_redoc_url = "/redoc" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None

app = FastAPI(
    title="MamaBird Chatbot API",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"http://localhost:\d+",  # Flutter web / local dev on any port
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
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # The white-label demo page is a real HTML document with inline CSS/JS that
    # fetches the same-origin demo API; the API's default `default-src 'none'`
    # would break it, so give just that one route a page-appropriate policy.
    if request.url.path == "/demo/business/page":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; form-action 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    logger.info("RES %s %s %s %dms", request_id, request.method, request.url.path, duration_ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Return a generic message so field names / schema are not leaked to clients.
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Validation error [%s] on %s: %s", request_id, request.url.path, exc)
    return JSONResponse(status_code=422, content={"detail": "Invalid request data"})


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
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(classrooms.router)
app.include_router(demo_business.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MamaBird API is running"}
