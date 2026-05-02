"""
Unit tests for Pydantic schemas (backend/schemas/pydantic_models.py).

Covers: validation, JSON field parsing, required vs optional fields,
and serialization round-trips.
"""
import json
import pytest
from datetime import datetime, date
from pydantic import ValidationError

from backend.schemas.pydantic_models import (
    VesselRead, VesselCreate, VesselUpdate,
    CrewMemberRead, CrewMemberCreate, CrewMemberUpdate,
    HealthEventRead, HealthEventCreate, VitalSigns,
    ComponentRead, ComponentCreate, ComponentUpdate,
    MaintenanceLogRead, MaintenanceLogCreate,
    SyncQueueRead, SyncStatusRead,
    MedicalQueryRequest, ComponentAnalysisRequest,
)


# ── VesselSchemas ────────────────────────────────────────────────────────────

class TestVesselSchemas:
    def test_vessel_create_minimal(self):
        v = VesselCreate(name="Test Vessel")
        assert v.name == "Test Vessel"
        assert v.imo_number is None

    def test_vessel_create_full(self):
        v = VesselCreate(name="MV Resolute", imo_number="9876543")
        assert v.imo_number == "9876543"

    def test_vessel_create_missing_name(self):
        with pytest.raises(ValidationError):
            VesselCreate()

    def test_vessel_update_partial(self):
        v = VesselUpdate(name="Renamed")
        assert v.name == "Renamed"
        assert v.imo_number is None

    def test_vessel_read_from_attributes(self):
        """Simulates from_attributes (ORM mode) with a mock object."""
        class FakeVessel:
            vessel_id = "v-1"
            name = "MV Test"
            imo_number = "1111111"
            created_at = datetime(2025, 1, 1, 0, 0, 0)

        v = VesselRead.model_validate(FakeVessel())
        assert v.vessel_id == "v-1"
        assert v.name == "MV Test"


# ── CrewMember Schemas ───────────────────────────────────────────────────────

class TestCrewMemberSchemas:
    def test_crew_create_minimal(self):
        c = CrewMemberCreate(vessel_id="v-1", full_name="Test Person", role="Deckhand")
        assert c.full_name == "Test Person"
        assert c.allergies is None

    def test_crew_create_with_allergies(self):
        c = CrewMemberCreate(
            vessel_id="v-1", full_name="Test", role="Cook",
            allergies=["Shellfish", "Penicillin"]
        )
        assert len(c.allergies) == 2

    def test_crew_read_parses_json_allergies(self):
        """CrewMemberRead should parse a JSON string into a list."""
        class FakeCrew:
            crew_id = "c-1"
            vessel_id = "v-1"
            full_name = "Test"
            role = "AB"
            date_of_birth = None
            blood_type = "B+"
            allergies = '["Aspirin", "Latex"]'
            medical_notes = None
            emergency_contact = None
            is_active = True
            created_at = None

        c = CrewMemberRead.model_validate(FakeCrew())
        assert c.allergies == ["Aspirin", "Latex"]

    def test_crew_read_parses_json_emergency_contact(self):
        class FakeCrew:
            crew_id = "c-1"
            vessel_id = "v-1"
            full_name = "Test"
            role = "AB"
            date_of_birth = None
            blood_type = None
            allergies = None
            medical_notes = None
            emergency_contact = '{"name": "Jane", "phone": "+1234"}'
            is_active = True
            created_at = None

        c = CrewMemberRead.model_validate(FakeCrew())
        assert c.emergency_contact["name"] == "Jane"

    def test_crew_read_handles_invalid_json_allergies(self):
        class FakeCrew:
            crew_id = "c-1"
            vessel_id = "v-1"
            full_name = "Test"
            role = "AB"
            date_of_birth = None
            blood_type = None
            allergies = "not-valid-json"
            medical_notes = None
            emergency_contact = None
            is_active = True
            created_at = None

        c = CrewMemberRead.model_validate(FakeCrew())
        assert c.allergies == []

    def test_crew_update_partial(self):
        u = CrewMemberUpdate(blood_type="AB+")
        data = u.model_dump(exclude_unset=True)
        assert "blood_type" in data
        assert "full_name" not in data

    def test_crew_create_missing_required(self):
        with pytest.raises(ValidationError):
            CrewMemberCreate(vessel_id="v-1")  # missing full_name, role


# ── VitalSigns ───────────────────────────────────────────────────────────────

class TestVitalSigns:
    def test_vital_signs_full(self):
        v = VitalSigns(hr=72, bp="120/80", temp=36.6, spo2=98, rr=16)
        assert v.hr == 72
        assert v.temp == 36.6

    def test_vital_signs_partial(self):
        v = VitalSigns(hr=90)
        assert v.bp is None
        assert v.spo2 is None

    def test_vital_signs_empty(self):
        v = VitalSigns()
        assert v.hr is None


# ── HealthEvent Schemas ──────────────────────────────────────────────────────

class TestHealthEventSchemas:
    def test_health_event_create_minimal(self):
        h = HealthEventCreate(
            vessel_id="v-1", crew_id="c-1", logged_by="c-2", severity="minor"
        )
        assert h.symptoms is None
        assert h.follow_up_required is False

    def test_health_event_create_with_vitals(self):
        h = HealthEventCreate(
            vessel_id="v-1", crew_id="c-1", logged_by="c-2",
            severity="serious",
            vital_signs=VitalSigns(hr=120, bp="90/60", spo2=92),
        )
        assert h.vital_signs.hr == 120

    def test_health_event_read_parses_json_symptoms(self):
        class FakeEvent:
            event_id = "e-1"
            vessel_id = "v-1"
            crew_id = "c-1"
            logged_by = "c-2"
            event_time = datetime.utcnow()
            symptoms = '["fever", "cough"]'
            vital_signs = None
            diagnosis = None
            treatment = None
            protocol_used = None
            ai_response = None
            severity = "moderate"
            follow_up_required = False
            synced = False
            created_at = None

        h = HealthEventRead.model_validate(FakeEvent())
        assert h.symptoms == ["fever", "cough"]

    def test_health_event_read_parses_json_vitals(self):
        class FakeEvent:
            event_id = "e-1"
            vessel_id = "v-1"
            crew_id = "c-1"
            logged_by = "c-2"
            event_time = datetime.utcnow()
            symptoms = None
            vital_signs = '{"hr": 88, "bp": "130/85"}'
            diagnosis = None
            treatment = None
            protocol_used = None
            ai_response = None
            severity = "moderate"
            follow_up_required = False
            synced = False
            created_at = None

        h = HealthEventRead.model_validate(FakeEvent())
        assert h.vital_signs["hr"] == 88


# ── Component Schemas ────────────────────────────────────────────────────────

class TestComponentSchemas:
    def test_component_create(self):
        c = ComponentCreate(
            vessel_id="v-1", name="Bilge Pump", system="hull",
            spare_parts=["Impeller", "Seal kit"],
        )
        assert len(c.spare_parts) == 2

    def test_component_read_parses_spare_parts(self):
        class FakeComp:
            component_id = "c-1"
            vessel_id = "v-1"
            name = "Pump"
            system = "hull"
            manufacturer = None
            model_number = None
            serial_number = None
            install_date = None
            location = None
            manual_ref = None
            spare_parts = '["Gasket", "Bearing"]'
            photo_path = None
            notes = None
            is_active = True
            created_at = None

        c = ComponentRead.model_validate(FakeComp())
        assert c.spare_parts == ["Gasket", "Bearing"]

    def test_component_update_partial(self):
        u = ComponentUpdate(notes="Replaced bearing")
        data = u.model_dump(exclude_unset=True)
        assert "notes" in data
        assert "name" not in data


# ── MaintenanceLog Schemas ───────────────────────────────────────────────────

class TestMaintenanceLogSchemas:
    def test_maintenance_create(self):
        m = MaintenanceLogCreate(
            vessel_id="v-1", component_id="c-1", logged_by="crew-1",
            issue_description="Oil leak", severity="critical",
        )
        assert m.severity == "critical"

    def test_maintenance_read_parses_json_lists(self):
        class FakeLog:
            log_id = "m-1"
            vessel_id = "v-1"
            component_id = "c-1"
            logged_by = "crew-1"
            event_time = datetime.utcnow()
            issue_description = "Test"
            photo_paths = '["img1.jpg", "img2.jpg"]'
            ai_diagnosis = None
            ai_guidance = None
            parts_used = '["Seal", "Bolt"]'
            action_taken = None
            resolved = False
            severity = "advisory"
            follow_up = None
            synced = False
            created_at = None

        m = MaintenanceLogRead.model_validate(FakeLog())
        assert m.photo_paths == ["img1.jpg", "img2.jpg"]
        assert m.parts_used == ["Seal", "Bolt"]


# ── AI Request Schemas ───────────────────────────────────────────────────────

class TestAISchemas:
    def test_medical_query_request(self):
        req = MedicalQueryRequest(
            crew_id="c-1", symptoms=["burns", "pain"], severity="serious"
        )
        assert len(req.symptoms) == 2

    def test_medical_query_missing_symptoms(self):
        with pytest.raises(ValidationError):
            MedicalQueryRequest(crew_id="c-1", severity="minor")

    def test_component_analysis_request(self):
        req = ComponentAnalysisRequest(
            component_id="c-1", issue_description="Won't start", severity="critical"
        )
        assert req.severity == "critical"


# ── SyncQueue Schemas ────────────────────────────────────────────────────────

class TestSyncSchemas:
    def test_sync_status_read(self):
        s = SyncStatusRead(queue_depth=5)
        assert s.queue_depth == 5
        assert s.last_sync is None
