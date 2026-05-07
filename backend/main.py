import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.db.database import Base, engine
from backend.routers import crew, health, vessel, maintenance, ai, sync, setup, uploads

app = FastAPI(
    title="Vessel Ops AI",
    description="Offline AI assistant for maritime Medical Person in Charge and Chief Engineer",
    version="0.1.0",
)

# Serve uploads as static files
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Serve manuals as static files
_MANUALS_DIR = Path(__file__).parent / "data" / "manuals"
if _MANUALS_DIR.is_dir():
    app.mount("/manuals", StaticFiles(directory=str(_MANUALS_DIR)), name="manuals")

# Create tables on startup (Alembic handles migrations in production)
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz", tags=["system"])
@app.get("/healthz/", tags=["system"])
def healthcheck():
    return {"status": "ok", "service": "vessel-ops-ai", "version": "0.1.2"}


app.include_router(crew.router, prefix="/api/crew", tags=["crew"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(vessel.router, prefix="/api/components", tags=["vessel"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["maintenance"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])


# Serve the embedded Next.js static export when present (Docker / local dev).
# In the Cloud Run + Firebase Hosting deployment, frontend_out won't exist and
# Firebase serves the frontend directly — this block is simply skipped.
_FRONTEND = Path(__file__).parent.parent / "frontend_out"
if _FRONTEND.is_dir():
    # Serve Next.js assets
    app.mount("/_next", StaticFiles(directory=str(_FRONTEND / "_next")), name="nextjs-assets")
    
    # Serve public assets (images, etc)
    if (_FRONTEND / "images").is_dir():
        app.mount("/images", StaticFiles(directory=str(_FRONTEND / "images")), name="public-images")
    if (_FRONTEND / "favicon.ico").is_file():
        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            return FileResponse(str(_FRONTEND / "favicon.ico"))

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str = ""):
        # 1. Check if the path points directly to a file (images, robots.txt, manifest.json)
        file_path = _FRONTEND / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))

        # 2. Check for Next.js trailingSlash export (path/index.html)
        index_candidate = _FRONTEND / full_path / "index.html"
        if index_candidate.is_file():
            return FileResponse(str(index_candidate))

        # 3. Fallback to root index for SPA routing
        return FileResponse(str(_FRONTEND / "index.html"))
