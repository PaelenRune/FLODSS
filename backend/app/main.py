"""Main FastAPI application entrypoint for the Facility Layout Optimization System (FLODSS)."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import logging
from app.core.config import settings
from app.api.api import api_router
from app.db.database import db_manager
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

FRONTEND_DIST = (
    Path(settings.STATIC_DIR)
    if settings.STATIC_DIR
    else Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: runs DB schema migrations and bootstraps admin user."""
    db_manager.run_migrations()
    with db_manager.get_connection() as conn:
        AuthService.ensure_admin_user(conn)
    if settings.is_perimeter_enforced and settings.is_default_admin_password_used:
        logger.warning(
            "SECURITY ADVISORY: Default administrator password is currently configured! "
            "Execute 'python scripts/rotate_admin_credentials.py' to assign a secure random password."
        )
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Industrial Facility Layout Optimization & Decision Support System (FLODSS) - Controlled Research Access",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Enforce 10 MB maximum request payload size
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 10 * 1024 * 1024:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload Too Large: Maximum allowed upload size is 10 MB."},
                )
        except ValueError:
            pass
    return await call_next(request)


# Security response headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Configure Cross-Origin Resource Sharing (CORS) for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount primary API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount frontend static assets if available (compiled production build)
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")


@app.get("/", summary="Root Welcome & Single-Origin SPA")
def root(request: Request):
    """Serve single-origin frontend index.html for browsers, or JSON discovery for API clients."""
    accept = request.headers.get("accept", "")
    index_file = FRONTEND_DIST / "index.html"
    if "text/html" in accept and index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return {
        "message": "Welcome to Facility Layout Optimization & Decision Support System (FLODSS)",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "version": settings.VERSION,
    }


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa_or_static(full_path: str, request: Request):
    """Fallback handler to serve static frontend files or SPA index.html for browser routes."""
    if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not Found")

    target_file = FRONTEND_DIST / full_path
    if target_file.is_file() and not full_path.startswith(".."):
        return FileResponse(str(target_file))

    index_file = FRONTEND_DIST / "index.html"
    accept = request.headers.get("accept", "")
    if index_file.exists() and "text/html" in accept:
        return FileResponse(str(index_file), media_type="text/html")

    raise HTTPException(status_code=404, detail="Not Found")
