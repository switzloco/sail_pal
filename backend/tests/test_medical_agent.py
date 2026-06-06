"""
Tests for the Arize-instrumented medical triage agent and its guardrail evals.

The LLM and RAG layers are mocked so these run offline and deterministically.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── tracing (no-op path) ──────────────────────────────────────────────────────

class TestTracing:
    def test_init_disabled_returns_false(self):
        from backend.ai import tracing
        # conftest sets ARIZE_TRACING_ENABLED=false; reset the one-shot guard.
        tracing._INITIALIZED = False
        tracing._ENABLED = False
        assert tracing.init_tracing() is False
        assert tracing.is_enabled() is False

    def test_span_noop_is_safe(self):
        from backend.ai import tracing
        with tracing.span("x", kind=tracing.TOOL, input_value="hi") as span:
            span.set("k", "v")
            span.set("none", None)
            span.set_output("done")  # must not raise when tracing is off

    def test_backend_name_default(self):
        from backend.ai import tracing
        assert isinstance(tracing.backend_name(), str)


# ── evals ─────────────────────────────────────────────────────────────────────

class TestEvals:
    def test_parse_verdict_grounded(self):
        from backend.ai.evals import _parse_verdict
        v = _parse_verdict('{"label": "grounded", "score": 0.9, "explanation": "ok"}')
        assert v["label"] == "grounded"
        assert v["score"] == 0.9

    def test_parse_verdict_clamps_and_labels(self):
        from backend.ai.evals import _parse_verdict
        v = _parse_verdict('noise {"label":"bad","score":5,"explanation":"x"} tail')
        assert v["label"] == "hallucinated"
        assert v["score"] == 1.0

    def test_parse_verdict_unparseable(self):
        from backend.ai.evals import _parse_verdict
        v = _parse_verdict("not json at all")
        assert v["label"] == "unknown"
        assert v["score"] == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_groundedness_passed(self):
        from backend.ai import evals
        with patch.object(
            evals, "llm_complete",
            AsyncMock(return_value='{"label":"grounded","score":0.95,"explanation":"fully supported"}'),
        ):
            v = await evals.evaluate_groundedness(
                "fever", "Give fluids [WHO, p.1]", [{"text": "give fluids", "metadata": {}}]
            )
        assert v["passed"] is True
        assert v["score"] == 0.95

    @pytest.mark.asyncio
    async def test_evaluate_groundedness_failed_below_threshold(self):
        from backend.ai import evals
        with patch.object(
            evals, "llm_complete",
            AsyncMock(return_value='{"label":"hallucinated","score":0.2,"explanation":"made up dose"}'),
        ):
            v = await evals.evaluate_groundedness("fever", "Give 500mg X", [])
        assert v["passed"] is False


# ── shared LLM routing ────────────────────────────────────────────────────────

class TestLLMRouting:
    @pytest.mark.asyncio
    async def test_llm_tokens_local_ollama_path(self):
        from backend.ai import llm

        class FakeRouter:
            def __init__(self, **kwargs):
                pass

            async def chat_stream(self, *a, **k):
                for t in ["a", "b"]:
                    yield t

        with patch.object(llm.mode_state, "is_cloud", return_value=False), \
             patch("backend.ai.ollama_client.OllamaRouter", FakeRouter):
            out = [t async for t in llm.llm_tokens("sys", "hi")]
        assert out == ["a", "b"]

    @pytest.mark.asyncio
    async def test_llm_complete_concatenates(self):
        from backend.ai import llm

        async def fake_tokens(*a, **k):
            for t in ["x", "y", "z"]:
                yield t

        with patch.object(llm, "llm_tokens", fake_tokens):
            assert await llm.llm_complete("sys", "p") == "xyz"


# ── agent tools ───────────────────────────────────────────────────────────────

class TestAgentTools:
    def test_lookup_crew_member_found(self, db, seed_crew):
        from backend.ai.agent import MedicalTriageAgent
        agent = MedicalTriageAgent(db)
        rec = agent.lookup_crew_member(seed_crew[0].crew_id)
        assert rec["full_name"] == "John Smith"
        assert rec["allergies"] == ["Penicillin"]

    def test_lookup_crew_member_missing(self, db):
        from backend.ai.agent import MedicalTriageAgent
        agent = MedicalTriageAgent(db)
        assert agent.lookup_crew_member("nope") is None

    def test_retrieve_protocol_uses_rag(self, db):
        from backend.ai import agent as agent_mod
        fake_engine = MagicMock()
        fake_engine.query.return_value = [{"text": "rest", "metadata": {"source": "WHO", "page": 5}}]
        with patch.object(agent_mod, "_rag_engine", return_value=fake_engine):
            agent = agent_mod.MedicalTriageAgent(db)
            out = agent.retrieve_protocol(["fever"])
        assert out[0]["metadata"]["source"] == "WHO"
        fake_engine.query.assert_called_once()


# ── agent orchestration ───────────────────────────────────────────────────────

async def _fake_tokens(*args, **kwargs):
    for t in ["Keep ", "patient ", "warm. [WHO, p.5]"]:
        yield t


async def _collect(agen):
    return [e async for e in agen]


class TestAgentRun:
    @pytest.mark.asyncio
    async def test_run_happy_path_logs_event(self, db, seed_crew):
        from backend.ai import agent as agent_mod
        fake_engine = MagicMock()
        fake_engine.query.return_value = [{"text": "keep warm", "metadata": {"source": "WHO", "page": 5}}]

        with patch.object(agent_mod, "_rag_engine", return_value=fake_engine), \
             patch.object(agent_mod, "llm_tokens", _fake_tokens), \
             patch.object(agent_mod, "evaluate_groundedness",
                          AsyncMock(return_value={"label": "grounded", "score": 0.9,
                                                  "explanation": "ok", "passed": True})):
            agent = agent_mod.MedicalTriageAgent(db)
            events = await _collect(agent.run(
                crew_id=seed_crew[0].crew_id,
                symptoms=["hypothermia"],
                severity="serious",
            ))

        types = [e["type"] for e in events]
        assert types[0] == "plan"
        assert "token" in types
        assert "eval" in types
        assert types[-1] == "done"

        done = events[-1]
        assert done["eval_passed"] is True
        assert done["event_id"] is not None

        # Health event actually written to the DB.
        from backend.db.models import HealthEvent
        evt = db.query(HealthEvent).filter(HealthEvent.event_id == done["event_id"]).first()
        assert evt is not None
        assert evt.crew_id == seed_crew[0].crew_id
        assert "warm" in (evt.ai_response or "")

    @pytest.mark.asyncio
    async def test_run_crew_not_found_emits_error(self, db):
        from backend.ai import agent as agent_mod
        agent = agent_mod.MedicalTriageAgent(db)
        events = await _collect(agent.run(crew_id="ghost", symptoms=["x"], severity="minor"))
        assert any(e["type"] == "error" for e in events)
        assert not any(e["type"] == "done" for e in events)

    @pytest.mark.asyncio
    async def test_run_failed_eval_triggers_regeneration(self, db, seed_crew):
        from backend.ai import agent as agent_mod
        fake_engine = MagicMock()
        fake_engine.query.return_value = [{"text": "give fluids", "metadata": {"source": "WHO", "page": 2}}]

        # First eval fails, second (after stricter regen) passes.
        eval_mock = AsyncMock(side_effect=[
            {"label": "hallucinated", "score": 0.2, "explanation": "made up", "passed": False},
            {"label": "grounded", "score": 0.8, "explanation": "ok", "passed": True},
        ])

        with patch.object(agent_mod, "_rag_engine", return_value=fake_engine), \
             patch.object(agent_mod, "llm_tokens", _fake_tokens), \
             patch.object(agent_mod, "evaluate_groundedness", eval_mock):
            agent = agent_mod.MedicalTriageAgent(db)
            events = await _collect(agent.run(
                crew_id=seed_crew[0].crew_id, symptoms=["fever"], severity="moderate",
            ))

        assert any(e["type"] == "regenerate" for e in events)
        assert eval_mock.await_count == 2
        assert events[-1]["eval_passed"] is True

    @pytest.mark.asyncio
    async def test_run_auto_log_false_skips_db_write(self, db, seed_crew):
        from backend.ai import agent as agent_mod
        fake_engine = MagicMock()
        fake_engine.query.return_value = []

        with patch.object(agent_mod, "_rag_engine", return_value=fake_engine), \
             patch.object(agent_mod, "llm_tokens", _fake_tokens), \
             patch.object(agent_mod, "evaluate_groundedness",
                          AsyncMock(return_value={"label": "grounded", "score": 0.9,
                                                  "explanation": "ok", "passed": True})):
            agent = agent_mod.MedicalTriageAgent(db)
            events = await _collect(agent.run(
                crew_id=seed_crew[0].crew_id, symptoms=["cut"], severity="minor", auto_log=False,
            ))
        assert events[-1]["event_id"] is None


# ── endpoint ──────────────────────────────────────────────────────────────────

class TestMedicalAgentEndpoint:
    def test_404_when_crew_missing(self, client):
        r = client.post("/api/ai/medical-agent", json={
            "crew_id": "nobody", "symptoms": ["fever"], "severity": "minor",
        })
        assert r.status_code == 404

    def test_stream_runs_agent(self, client, seed_crew):
        from backend.ai import agent as agent_mod
        fake_engine = MagicMock()
        fake_engine.query.return_value = [{"text": "rest", "metadata": {"source": "WHO", "page": 1}}]

        with patch.object(agent_mod, "_rag_engine", return_value=fake_engine), \
             patch.object(agent_mod, "llm_tokens", _fake_tokens), \
             patch.object(agent_mod, "evaluate_groundedness",
                          AsyncMock(return_value={"label": "grounded", "score": 0.9,
                                                  "explanation": "ok", "passed": True})):
            r = client.post("/api/ai/medical-agent", json={
                "crew_id": seed_crew[0].crew_id,
                "symptoms": ["headache"],
                "severity": "minor",
            })
        assert r.status_code == 200
        body = r.text
        assert '"type": "plan"' in body
        assert '"type": "done"' in body
