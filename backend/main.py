from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/", tags=["system"])
def healthcheck():
    return {"status": "ok", "service": "vessel-ops-ai"}
