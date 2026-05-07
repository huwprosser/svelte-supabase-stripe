from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

from config import (
    FRONTEND_URL,
    IS_PRODUCTION,
    MAX_REQUEST_BODY_BYTES,
    require_configured_stripe_webhook_secret,
)
from routes.payments import router as payments_router
from routes.telemetry import router as telemetry_router
from routes.user import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if IS_PRODUCTION:
        require_configured_stripe_webhook_secret()
    yield


app = FastAPI(
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self' https://www.googletagmanager.com https://www.google-analytics.com; connect-src 'self' https://*.supabase.co https://www.google-analytics.com; img-src 'self' data: https://www.google-analytics.com; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    try:
        is_too_large = bool(content_length) and int(content_length) > MAX_REQUEST_BODY_BYTES
    except ValueError:
        is_too_large = True

    if is_too_large:
        response = JSONResponse({"detail": "Request body too large"}, status_code=413)
    else:
        response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if IS_PRODUCTION:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response
app.include_router(user_router)
app.include_router(payments_router)
app.include_router(telemetry_router)

# In Docker, the built SvelteKit app is copied to server/static.
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    def safe_static_file(path: str) -> Path | None:
        try:
            requested_file = (STATIC_DIR / path).resolve()
            static_root = STATIC_DIR.resolve()
            requested_file.relative_to(static_root)
        except (OSError, RuntimeError, ValueError):
            return None
        return requested_file if requested_file.is_file() else None

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        requested_file = safe_static_file(path) if path else None
        if requested_file:
            return FileResponse(requested_file)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
