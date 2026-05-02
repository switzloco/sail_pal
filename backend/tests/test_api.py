"""
Integration tests for API endpoints (backend/routers/).
Uses FastAPI TestClient with an isolated SQLite database.
"""
import json
import pytest


class TestHealthcheck:
    def test_healthcheck(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestCrewRouter:
    def test_list_crew_empty(self, client):
        r = client.get("/api/crew")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_crew_member(self, client, seed_vessel):
        payload = {
            "vessel_id": seed_vessel.vessel_id,
            "full_name": "New Person",
            "role": "Bosun",
            "blood_type": "O-",
            "allergies": ["Ibuprofen"],
        }
        r = client.post("/api/crew", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["full_name"] == "New Person"
        assert data["allergies"] == ["Ibuprofen"]

    def test_get_crew_member(self, client, seed_crew):
        r = client.get(f"/api/crew/{seed_crew[0].crew_id}")
        assert r.status_code == 200
        assert r.json()["full_name"] == "John Smith"

    def test_get_crew_not_found(self, client):
        r = client.get("/api/crew/nonexistent")
        assert r.status_code == 404

    def test_update_crew_member(self, client, seed_crew):
        r = client.patch(
            f"/api/crew/{seed_crew[0].crew_id}",
            json={"blood_type": "AB+"},
        )
        assert r.status_code == 200
        assert r.json()["blood_type"] == "AB+"
        assert r.json()["full_name"] == "John Smith"

    def test_delete_crew_member(self, client, seed_crew):
        r = client.delete(f"/api/crew/{seed_crew[0].crew_id}")
        assert r.status_code == 204
        r = client.get(f"/api/crew/{seed_crew[0].crew_id}")
        assert r.status_code == 404

    def test_list_crew_filters_inactive(self, client, seed_crew):
        client.patch(f"/api/crew/{seed_crew[0].crew_id}", json={"is_active": False})
        r = client.get("/api/crew")
        names = [m["full_name"] for m in r.json()]
        assert "John Smith" not in names


class TestComponentRouter:
    def test_create_component(self, client, seed_vessel):
        payload = {
            "vessel_id": seed_vessel.vessel_id,
            "name": "Generator", "system": "electrical",
        }
        r = client.post("/api/components", json=payload)
        assert r.status_code == 201
        assert r.json()["system"] == "electrical"

    def test_get_component_not_found(self, client):
        r = client.get("/api/components/nonexistent")
        assert r.status_code == 404

    def test_update_component(self, client, seed_component):
        r = client.patch(
            f"/api/components/{seed_component.component_id}",
            json={"notes": "Scheduled for overhaul"},
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Scheduled for overhaul"

    def test_filter_by_system(self, client, seed_vessel):
        client.post("/api/components", json={
            "vessel_id": seed_vessel.vessel_id, "name": "Radar", "system": "navigation",
        })
        client.post("/api/components", json={
            "vessel_id": seed_vessel.vessel_id, "name": "Pump", "system": "hull",
        })
        r = client.get("/api/components?system=navigation")
        assert len(r.json()) == 1


class TestHealthRouter:
    def test_create_health_event(self, client, seed_vessel, seed_crew):
        payload = {
            "vessel_id": seed_vessel.vessel_id,
            "crew_id": seed_crew[0].crew_id,
            "logged_by": seed_crew[1].crew_id,
            "symptoms": ["fever"], "severity": "moderate",
        }
        r = client.post("/api/health/events", json=payload)
        assert r.status_code == 201

    def test_get_health_event_not_found(self, client):
        r = client.get("/api/health/events/nonexistent")
        assert r.status_code == 404

    def test_crew_health_history(self, client, seed_health_event):
        r = client.get(f"/api/health/crew/{seed_health_event.crew_id}/history")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestMaintenanceRouter:
    def test_create_maintenance_log(self, client, seed_vessel, seed_crew, seed_component):
        r = client.post("/api/maintenance/logs", data={
            "vessel_id": seed_vessel.vessel_id,
            "component_id": seed_component.component_id,
            "logged_by": seed_crew[1].crew_id,
            "issue_description": "Oil pressure warning",
            "severity": "critical",
        })
        assert r.status_code == 201

    def test_get_log_not_found(self, client):
        r = client.get("/api/maintenance/logs/nonexistent")
        assert r.status_code == 404


class TestSyncRouter:
    def test_sync_status(self, client):
        r = client.get("/api/sync/status")
        assert r.status_code == 200
        assert r.json()["queue_depth"] == 0

    def test_sync_now_not_implemented(self, client):
        r = client.post("/api/sync/now")
        assert r.status_code == 501


class TestSetupRouter:
    def test_get_vessel_info_creates_default(self, client):
        r = client.get("/api/setup/vessel-info")
        assert r.status_code == 200
        assert "vessel_id" in r.json()

    def test_update_vessel_info(self, client):
        client.get("/api/setup/vessel-info")
        r = client.post("/api/setup/vessel-info", json={"name": "MV Enterprise"})
        assert r.status_code == 200
        assert r.json()["name"] == "MV Enterprise"

    def test_get_mode(self, client):
        r = client.get("/api/setup/mode")
        assert r.status_code == 200
        assert r.json()["mode"] in ("cloud", "local")

    def test_reset_demo_data(self, client, seed_vessel, seed_crew):
        assert len(client.get("/api/crew").json()) > 0
        r = client.post("/api/setup/reset-demo-data")
        assert r.status_code == 200
        assert len(client.get("/api/crew").json()) == 0
