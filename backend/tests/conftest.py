"""
Shared pytest fixtures for the Vessel Ops AI backend test suite.

Uses an in-memory SQLite database so tests are fast, isolated,
and don't touch the production vessel.db file.
"""
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Environment overrides (must happen BEFORE any backend imports) ───────────
os.environ["DATABASE_URL"] = "sqlite:///./test_vessel.db"
os.environ["CLOUD_MODE"] = "false"
os.environ["GOOGLE_API_KEY"] = "test-key-not-real"
# Keep the test suite hermetic: never try to ship traces to Arize/Phoenix.
os.environ["ARIZE_TRACING_ENABLED"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base, get_db
from backend.db.models import (
    Vessel, CrewMember, Component, HealthEvent, MaintenanceLog, SyncQueue,
)
from backend.main import app


# ── In-memory SQLite engine ──────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_vessel.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _set_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ── Database lifecycle ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    """Provide a clean database session for direct model testing."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """TestClient wired to the overridden DB."""
    return TestClient(app)


# ── Seed data fixtures ──────────────────────────────────────────────────────

@pytest.fixture()
def seed_vessel(db):
    """Insert a single test vessel and return it."""
    vessel = Vessel(vessel_id="test-vessel-1", name="MV Test Ship", imo_number="1234567")
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return vessel


@pytest.fixture()
def seed_crew(db, seed_vessel):
    """Insert two crew members and return them as a list."""
    members = [
        CrewMember(
            crew_id="crew-1",
            vessel_id=seed_vessel.vessel_id,
            full_name="John Smith",
            role="Captain",
            blood_type="O+",
            allergies=json.dumps(["Penicillin"]),
            medical_notes="History of seasickness",
        ),
        CrewMember(
            crew_id="crew-2",
            vessel_id=seed_vessel.vessel_id,
            full_name="Jane Doe",
            role="Chief Engineer",
            blood_type="A-",
            allergies=json.dumps([]),
        ),
    ]
    db.add_all(members)
    db.commit()
    for m in members:
        db.refresh(m)
    return members


@pytest.fixture()
def seed_component(db, seed_vessel):
    """Insert a test component and return it."""
    comp = Component(
        component_id="comp-1",
        vessel_id=seed_vessel.vessel_id,
        name="Main Engine",
        system="propulsion",
        manufacturer="MAN B&W",
        model_number="6S50MC-C",
        location="Engine Room",
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


@pytest.fixture()
def seed_health_event(db, seed_vessel, seed_crew):
    """Insert a test health event and return it."""
    evt = HealthEvent(
        event_id="evt-1",
        vessel_id=seed_vessel.vessel_id,
        crew_id="crew-1",
        logged_by="crew-2",
        symptoms=json.dumps(["headache", "nausea"]),
        vital_signs=json.dumps({"hr": 88, "bp": "130/85", "temp": 37.2}),
        severity="moderate",
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


@pytest.fixture()
def seed_maintenance_log(db, seed_vessel, seed_crew, seed_component):
    """Insert a test maintenance log and return it."""
    log = MaintenanceLog(
        log_id="mlog-1",
        vessel_id=seed_vessel.vessel_id,
        component_id=seed_component.component_id,
        logged_by="crew-2",
        issue_description="Unusual vibration at 80% load",
        severity="degraded",
        photo_paths=json.dumps([]),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
