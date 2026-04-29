import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.db.database import Base, engine
from backend.routers import crew, health, vessel, maintenance, ai, sync, setup

# Create tables on startup (Alembic handles migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vessel Ops AI",
    description="Offline AI assistant for maritime Medical Person in Charge and Chief Engineer",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crew.router, prefix="/crew", tags=["crew"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(vessel.router, prefix="/components", tags=["vessel"])
app.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(setup.router, prefix="/setup", tags=["setup"])


@app.get("/healthz", tags=["system"])
def healthcheck():
    return {"status": "ok", "service": "vessel-ops-ai"}


# Serve the embedded Next.js static export when present (Docker / local dev).
# In the Cloud Run + Firebase Hosting deployment, frontend_out won't exist and
# Firebase serves the frontend directly — this block is simply skipped.
_FRONTEND = Path(__file__).parent.parent / "frontend_out"
if _FRONTEND.is_dir():
    app.mount("/_next", StaticFiles(directory=str(_FRONTEND / "_next")), name="nextjs-assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str = ""):
        # Serve the page's own index.html if it exists (Next.js trailingSlash export),
        # otherwise fall back to the root index for client-side routing.
        candidate = _FRONTEND / full_path / "index.html"
        if candidate.is_file():
            return FileResponse(str(candidate))
        root_index = _FRONTEND / "index.html"
        return FileResponse(str(root_index))
