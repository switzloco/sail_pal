"""
Unit tests for SQLAlchemy ORM models (backend/db/models.py).

Covers: table creation, relationships, constraints, defaults, and FK integrity.
"""
import json
import uuid
import pytest
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError

from backend.db.models import (
    Vessel, CrewMember, Component, HealthEvent, MaintenanceLog, SyncQueue, _uuid,
)


# ── UUID helper ──────────────────────────────────────────────────────────────

class TestUUIDHelper:
    def test_uuid_returns_string(self):
        result = _uuid()
        assert isinstance(result, str)

    def test_uuid_is_valid_v4(self):
        result = _uuid()
        parsed = uuid.UUID(result)
        assert parsed.version == 4

    def test_uuid_uniqueness(self):
        ids = {_uuid() for _ in range(100)}
        assert len(ids) == 100, "UUIDs should be unique"


# ── Vessel ───────────────────────────────────────────────────────────────────

class TestVesselModel:
    def test_create_vessel(self, db, seed_vessel):
        vessel = db.query(Vessel).filter(Vessel.vessel_id == "test-vessel-1").first()
        assert vessel is not None
        assert vessel.name == "MV Test Ship"
        assert vessel.imo_number == "1234567"

    def test_vessel_created_at_default(self, db, seed_vessel):
        assert seed_vessel.created_at is not None
        assert isinstance(seed_vessel.created_at, datetime)

    def test_vessel_relationships(self, db, seed_vessel, seed_crew, seed_component):
        vessel = db.query(Vessel).filter(Vessel.vessel_id == seed_vessel.vessel_id).first()
        assert len(vessel.crew_members) == 2
        assert len(vessel.components) == 1


# ── CrewMember ───────────────────────────────────────────────────────────────

class TestCrewMemberModel:
    def test_create_crew_member(self, db, seed_crew):
        member = db.query(CrewMember).filter(CrewMember.crew_id == "crew-1").first()
        assert member.full_name == "John Smith"
        assert member.role == "Captain"
        assert member.blood_type == "O+"

    def test_crew_member_default_active(self, db, seed_crew):
        member = db.query(CrewMember).filter(CrewMember.crew_id == "crew-1").first()
        assert member.is_active is True

    def test_crew_member_allergies_json(self, db, seed_crew):
        member = db.query(CrewMember).filter(CrewMember.crew_id == "crew-1").first()
        allergies = json.loads(member.allergies)
        assert allergies == ["Penicillin"]

    def test_crew_member_vessel_fk(self, db, seed_vessel):
        """Creating a crew member with a non-existent vessel_id should fail."""
        bad_member = CrewMember(
            crew_id="crew-bad",
            vessel_id="non-existent-vessel",
            full_name="Ghost",
            role="Nobody",
        )
        db.add(bad_member)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_crew_member_relationship_to_vessel(self, db, seed_crew):
        member = db.query(CrewMember).filter(CrewMember.crew_id == "crew-1").first()
        assert member.vessel is not None
        assert member.vessel.name == "MV Test Ship"


# ── Component ────────────────────────────────────────────────────────────────

class TestComponentModel:
    def test_create_component(self, db, seed_component):
        comp = db.query(Component).filter(Component.component_id == "comp-1").first()
        assert comp.name == "Main Engine"
        assert comp.system == "propulsion"
        assert comp.manufacturer == "MAN B&W"

    def test_component_default_active(self, db, seed_component):
        assert seed_component.is_active is True

    def test_component_system_constraint(self, db, seed_vessel):
        """System must be one of the allowed values."""
        bad_comp = Component(
            component_id="comp-bad",
            vessel_id=seed_vessel.vessel_id,
            name="Mystery Box",
            system="teleportation",  # not allowed
        )
        db.add(bad_comp)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_component_valid_systems(self, db, seed_vessel):
        """All valid system values should be accepted."""
        valid_systems = ["propulsion", "electrical", "navigation", "hvac", "safety", "hull"]
        for i, sys_name in enumerate(valid_systems):
            comp = Component(
                component_id=f"comp-valid-{i}",
                vessel_id=seed_vessel.vessel_id,
                name=f"Test {sys_name}",
                system=sys_name,
            )
            db.add(comp)
        db.commit()  # Should not raise


# ── HealthEvent ──────────────────────────────────────────────────────────────

class TestHealthEventModel:
    def test_create_health_event(self, db, seed_health_event):
        evt = db.query(HealthEvent).filter(HealthEvent.event_id == "evt-1").first()
        assert evt.severity == "moderate"
        symptoms = json.loads(evt.symptoms)
        assert "headache" in symptoms

    def test_health_event_severity_constraint(self, db, seed_vessel, seed_crew):
        """Severity must be one of the allowed values."""
        bad_evt = HealthEvent(
            event_id="evt-bad",
            vessel_id=seed_vessel.vessel_id,
            crew_id="crew-1",
            logged_by="crew-2",
            severity="apocalyptic",  # not allowed
        )
        db.add(bad_evt)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_health_event_valid_severities(self, db, seed_vessel, seed_crew):
        for i, sev in enumerate(["minor", "moderate", "serious", "critical"]):
            evt = HealthEvent(
                event_id=f"evt-sev-{i}",
                vessel_id=seed_vessel.vessel_id,
                crew_id="crew-1",
                logged_by="crew-2",
                severity=sev,
            )
            db.add(evt)
        db.commit()

    def test_health_event_relationships(self, db, seed_health_event):
        evt = db.query(HealthEvent).filter(HealthEvent.event_id == "evt-1").first()
        assert evt.crew_member.full_name == "John Smith"
        assert evt.logged_by_crew.full_name == "Jane Doe"
        assert evt.vessel.name == "MV Test Ship"


# ── MaintenanceLog ───────────────────────────────────────────────────────────

class TestMaintenanceLogModel:
    def test_create_maintenance_log(self, db, seed_maintenance_log):
        log = db.query(MaintenanceLog).filter(MaintenanceLog.log_id == "mlog-1").first()
        assert log.severity == "degraded"
        assert "vibration" in log.issue_description.lower()

    def test_maintenance_severity_constraint(self, db, seed_vessel, seed_crew, seed_component):
        bad_log = MaintenanceLog(
            log_id="mlog-bad",
            vessel_id=seed_vessel.vessel_id,
            component_id=seed_component.component_id,
            logged_by="crew-2",
            severity="catastrophic",  # not allowed
            photo_paths=json.dumps([]),
        )
        db.add(bad_log)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_maintenance_valid_severities(self, db, seed_vessel, seed_crew, seed_component):
        for i, sev in enumerate(["advisory", "degraded", "critical", "down"]):
            log = MaintenanceLog(
                log_id=f"mlog-sev-{i}",
                vessel_id=seed_vessel.vessel_id,
                component_id=seed_component.component_id,
                logged_by="crew-2",
                severity=sev,
                photo_paths=json.dumps([]),
            )
            db.add(log)
        db.commit()

    def test_maintenance_relationships(self, db, seed_maintenance_log):
        log = db.query(MaintenanceLog).filter(MaintenanceLog.log_id == "mlog-1").first()
        assert log.component.name == "Main Engine"
        assert log.logged_by_crew.full_name == "Jane Doe"


# ── SyncQueue ────────────────────────────────────────────────────────────────

class TestSyncQueueModel:
    def test_create_sync_entry(self, db):
        entry = SyncQueue(
            queue_id="sq-1",
            table_name="health_events",
            record_id="evt-1",
            operation="insert",
            payload=json.dumps({"test": True}),
        )
        db.add(entry)
        db.commit()

        saved = db.query(SyncQueue).filter(SyncQueue.queue_id == "sq-1").first()
        assert saved.operation == "insert"

    def test_sync_operation_constraint(self, db):
        bad = SyncQueue(
            queue_id="sq-bad",
            table_name="test",
            record_id="x",
            operation="destroy",  # not allowed
        )
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
