"""
Tests for the Fleet Mechanic evaluation pipeline.

These tests cover:
- EngineTrace / FleetEvaluation / PromptPatch DB models
- Fleet Mechanic API routes (trace upload, evaluation listing, patch workflow)
- Demo trace generation
- Arize Phoenix client (offline/graceful-degradation path)
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.fleet_mechanic.models import (
    EngineTraceCreate,
    MarinaSyncRequest,
    MarinaSyncReport,
    SensorData,
    ReasoningStep,
    PatchStatus,
)
from backend.fleet_mechanic.trace_recorder import generate_demo_trace, _SCENARIOS
from backend.fleet_mechanic.arize_client import ArizePhoenixClient


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_trace(vessel_id: str = "test-vessel") -> EngineTraceCreate:
    return EngineTraceCreate(
        vessel_id=vessel_id,
        component_name="raw_water_cooling",
        sensor_data=SensorData(
            rpm=2200.0,
            coolant_temp_c=98.5,
            oil_pressure_bar=3.2,
            exhaust_temp_c=520.0,
            fuel_flow_lph=12.5,
        ),
        model_prompt="Analyze coolant temperature anomaly.",
        model_response="Temperature slightly elevated. Continue monitoring.",
        reasoning_steps=[
            ReasoningStep(step=1, thought="Parsing sensor data", observation="Coolant 98.5°C"),
            ReasoningStep(step=2, thought="Checking thresholds", action="Compare to manufacturer spec"),
        ],
        diagnosis="Coolant temperature slightly elevated. Continue monitoring.",
        model_name="gemma4:e2b",
        recorded_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
    )


# ── Model / Pydantic validation tests ────────────────────────────────────────

class TestFleetMechanicModels:
    def test_trace_create_defaults(self):
        t = _make_trace()
        assert t.model_name == "gemma4:e2b"
        assert len(t.reasoning_steps) == 2
        assert t.sensor_data.coolant_temp_c == 98.5

    def test_sensor_data_partial(self):
        s = SensorData(rpm=1800.0)
        assert s.rpm == 1800.0
        assert s.coolant_temp_c is None
        assert s.raw_readings == {}

    def test_marina_sync_request(self):
        req = MarinaSyncRequest(traces=[_make_trace(), _make_trace()])
        assert len(req.traces) == 2

    def test_patch_status_enum(self):
        assert PatchStatus.pending.value == "pending"
        assert PatchStatus.deployed.value == "deployed"


# ── Trace recorder tests ──────────────────────────────────────────────────────

class TestTraceRecorder:
    def test_all_scenarios_exist(self):
        for name in ("impeller_failure", "oil_pressure_low", "governor_fault"):
            assert name in _SCENARIOS

    def test_correct_trace_generation(self):
        trace = generate_demo_trace("v-001", "impeller_failure", inject_hallucination=False)
        assert trace.vessel_id == "v-001"
        assert "impeller" in trace.diagnosis.lower() or "shutdown" in trace.diagnosis.lower()
        assert trace.sensor_data.coolant_temp_c == 98.5
        assert len(trace.reasoning_steps) == 3

    def test_hallucinated_trace_generation(self):
        trace = generate_demo_trace("v-001", "impeller_failure", inject_hallucination=True)
        # Hallucinated diagnosis minimises the issue
        assert "monitoring" in trace.diagnosis.lower() or "artifact" in trace.diagnosis.lower()

    def test_hours_ago_offset(self):
        trace = generate_demo_trace("v-001", hours_ago=12.0)
        delta = datetime.now(timezone.utc) - trace.recorded_at
        # Should be approximately 12 hours ago (±10 seconds for test execution)
        assert 11.9 * 3600 < delta.total_seconds() < 12.1 * 3600

    def test_unknown_scenario_falls_back(self):
        trace = generate_demo_trace("v-001", scenario="does_not_exist")
        assert trace.component_name == "raw_water_cooling"  # impeller_failure default


# ── Arize Phoenix client tests ────────────────────────────────────────────────

class TestArizePhoenixClient:
    @pytest.mark.asyncio
    async def test_health_check_unreachable(self):
        client = ArizePhoenixClient(base_url="http://127.0.0.1:19999")
        result = await client.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_ingest_trace_returns_id_when_phoenix_offline(self):
        """Client should return a trace ID even when Phoenix is unreachable."""
        client = ArizePhoenixClient(base_url="http://127.0.0.1:19999")
        trace = _make_trace()
        trace_id = await client.ingest_trace(trace, db_trace_id="db-123")
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    @pytest.mark.asyncio
    async def test_record_evaluation_silently_fails_offline(self):
        client = ArizePhoenixClient(base_url="http://127.0.0.1:19999")
        # Should not raise
        await client.record_evaluation(
            phoenix_trace_id="abc",
            eval_name="hallucination",
            label="fail",
            score=0.2,
            explanation="Test",
        )

    @pytest.mark.asyncio
    async def test_ingest_builds_correct_payload(self):
        """Verify the OpenInference span payload structure."""
        sent_payload = {}

        async def mock_post(url, json=None, headers=None):
            sent_payload.update(json or {})
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            return resp

        client = ArizePhoenixClient(base_url="http://phoenix:6006")
        trace = _make_trace()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(side_effect=mock_post)
            mock_client_cls.return_value = mock_ctx

            await client.ingest_trace(trace, "db-456")

        assert "resourceSpans" in sent_payload
        span = sent_payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attr_keys = [a["key"] for a in span["attributes"]]
        assert "openinference.span.kind" in attr_keys
        assert "input.value" in attr_keys
        assert "output.value" in attr_keys
        assert "engine.component" in attr_keys
        assert "engine.sensor_data" in attr_keys


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestFleetMechanicAPI:
    def test_list_traces_empty(self, client):
        resp = client.get("/api/fleet-mechanic/traces")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_evaluations_empty(self, client):
        resp = client.get("/api/fleet-mechanic/evaluations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_patches_empty(self, client):
        resp = client.get("/api/fleet-mechanic/patches")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_trace_404(self, client):
        resp = client.get("/api/fleet-mechanic/traces/nonexistent-id")
        assert resp.status_code == 404

    def test_patch_status_404(self, client):
        resp = client.patch("/api/fleet-mechanic/patches/nonexistent/status?status=approved")
        assert resp.status_code == 404

    def test_marina_sync_stores_traces(self, client):
        """Marina sync should persist traces to DB regardless of Gemini availability."""
        trace = _make_trace()
        # Patch out the Gemini calls so we don't need an API key in CI
        mock_report = MarinaSyncReport(
            sync_id=str(uuid.uuid4()),
            traces_ingested=1,
            evaluations_run=2,
            patches_generated=0,
            flagged_count=0,
            summary="1 trace analyzed: 1 passed.",
            trace_results=[{
                "db_id": "placeholder",
                "component": trace.component_name,
                "diagnosis": trace.diagnosis,
                "evaluations": [],
                "patches": [],
                "flagged": False,
                "phoenix_trace_id": "px-001",
            }],
        )

        with patch(
            "backend.routers.fleet_mechanic._make_agent"
        ) as mock_agent_factory:
            mock_agent = AsyncMock()
            mock_agent.process_marina_sync = AsyncMock(return_value=mock_report)
            mock_agent_factory.return_value = mock_agent

            payload = {
                "traces": [
                    {
                        "vessel_id": trace.vessel_id,
                        "component_name": trace.component_name,
                        "sensor_data": trace.sensor_data.model_dump(),
                        "model_prompt": trace.model_prompt,
                        "model_response": trace.model_response,
                        "reasoning_steps": [s.model_dump() for s in trace.reasoning_steps],
                        "diagnosis": trace.diagnosis,
                        "model_name": trace.model_name,
                        "recorded_at": trace.recorded_at.isoformat(),
                    }
                ]
            }
            resp = client.post("/api/fleet-mechanic/marina-sync", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["traces_ingested"] == 1

        # Verify trace is in DB
        list_resp = client.get("/api/fleet-mechanic/traces")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert list_resp.json()[0]["component_name"] == "raw_water_cooling"

    def test_trace_status_workflow(self, client):
        """Manually insert a patch and test the approve → deploy workflow."""
        from backend.db.database import SessionLocal
        from backend.db import models as db_models

        db = SessionLocal()
        try:
            trace_id = str(uuid.uuid4())
            trace = db_models.EngineTrace(
                id=trace_id,
                vessel_id="v-test",
                component_name="lubrication_system",
                sensor_data_json='{"rpm": 1800}',
                model_prompt="Test prompt",
                model_response="Test response",
                diagnosis="Low oil pressure",
                recorded_at=datetime.utcnow(),
                upload_status="evaluated",
            )
            db.add(trace)
            db.flush()

            patch_id = str(uuid.uuid4())
            patch = db_models.PromptPatch(
                id=patch_id,
                trace_id=trace_id,
                patch_type="system_instruction",
                patched_prompt_section="Add explicit oil pressure threshold check.",
                rationale="Test rationale",
                status="pending",
            )
            db.add(patch)
            db.commit()
        finally:
            db.close()

        resp = client.patch(f"/api/fleet-mechanic/patches/{patch_id}/status?status=approved")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        resp2 = client.patch(f"/api/fleet-mechanic/patches/{patch_id}/status?status=deployed")
        assert resp.status_code == 200
        assert resp2.json()["status"] == "deployed"

    def test_flagged_evaluations_filter(self, client):
        """?flagged_only=true should return only flagged evaluations."""
        from backend.db.database import SessionLocal
        from backend.db import models as db_models

        db = SessionLocal()
        try:
            trace_id = str(uuid.uuid4())
            trace = db_models.EngineTrace(
                id=trace_id,
                vessel_id="v-test",
                component_name="fuel_system",
                sensor_data_json="{}",
                model_prompt="p",
                model_response="r",
                diagnosis="d",
                recorded_at=datetime.utcnow(),
                upload_status="evaluated",
            )
            db.add(trace)
            db.flush()

            db.add(db_models.FleetEvaluation(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                evaluation_type="hallucination",
                score=0.9,
                label="pass",
                flagged=False,
            ))
            db.add(db_models.FleetEvaluation(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                evaluation_type="qa_correctness",
                score=0.3,
                label="fail",
                flagged=True,
            ))
            db.commit()
        finally:
            db.close()

        all_resp = client.get("/api/fleet-mechanic/evaluations")
        flagged_resp = client.get("/api/fleet-mechanic/evaluations?flagged_only=true")

        assert all_resp.status_code == 200
        assert flagged_resp.status_code == 200
        assert len(all_resp.json()) >= 2
        for e in flagged_resp.json():
            assert e["flagged"] is True
