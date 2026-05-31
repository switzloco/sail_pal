"""Tests for the Fleet Mechanic: trace capture, ingest/export, eval, patches.

The Gemini judge is mocked at `fleet_mechanic._gemini_json`, and Arize upload
is disabled (no creds in the test env → `arize_client.is_available()` is False),
so these run fully offline.
"""
import asyncio
import json

import pytest

from backend.ai.trace import traced_llm_tokens, trace_to_openinference
from backend.db.models import AITrace, PromptPatch
from backend.eval import fleet_mechanic, arize_client


# ── Trace capture ─────────────────────────────────────────────────────────────

async def _fake_tokens(parts):
    for p in parts:
        yield p


def _drain(aiter):
    async def _run():
        return [t async for t in aiter]
    return asyncio.run(_run())


def test_traced_llm_tokens_persists_and_passes_through(db):
    collected = _drain(
        traced_llm_tokens(
            _fake_tokens(["Apply ", "direct ", "pressure."]),
            route="medical_query",
            model_role="medical",
            model_name="hf.co/nswitzer/gemma4-maritime-medical-GGUF",
            system_prompt="SYS",
            user_prompt="bleeding wound",
            input_data={"symptoms": ["bleeding"]},
            rag_sources=[{"text": "Apply pressure", "metadata": {"source": "WHO IMGS"}}],
            severity="serious",
            crew_id="crew-1",
        )
    )
    # tokens pass through unchanged
    assert "".join(collected) == "Apply direct pressure."

    trace = db.query(AITrace).filter(AITrace.route == "medical_query").first()
    assert trace is not None
    assert trace.output_text == "Apply direct pressure."
    assert trace.model_role == "medical"
    assert trace.eval_label == "unevaluated"
    assert json.loads(trace.input_data) == {"symptoms": ["bleeding"]}
    assert int(trace.latency_ms) >= 0


def test_trace_to_openinference_shape(db):
    trace = AITrace(
        route="chat", model_role="medical", model_name="gemma4:e2b",
        system_prompt="SYS", user_prompt="hi", output_text="hello",
        input_data=json.dumps({"latest_message": "hi"}),
        rag_sources=json.dumps([{"text": "x"}]),
    )
    db.add(trace)
    db.commit()
    span = trace_to_openinference(trace)
    assert span["attributes"]["openinference.span.kind"] == "LLM"
    assert span["attributes"]["llm.model_name"] == "gemma4:e2b"
    assert span["attributes"]["metadata"]["input_data"] == {"latest_message": "hi"}


# ── Ingest / export endpoints ───────────────────────────────────────────────────

def _ingest_payload(**over):
    base = {
        "trace_id": "t-1",
        "route": "medical_query",
        "model_role": "medical",
        "model_name": "gemma4-medical",
        "system_prompt": "You are a maritime medical assistant.",
        "user_prompt": "Patient has chest pain.",
        "input_data": {"symptoms": ["chest pain"], "vitals": {"hr": 120}},
        "rag_sources": [{"text": "Aspirin 300mg for suspected MI", "metadata": {"source": "WHO IMGS"}}],
        "output_text": "Give 300mg aspirin and contact TMAS.",
        "severity": "critical",
    }
    base.update(over)
    return {"traces": [base]}


def test_ingest_is_idempotent(client):
    r1 = client.post("/api/traces", json=_ingest_payload())
    assert r1.status_code == 200
    assert r1.json() == {"ingested": 1, "skipped": 0}
    # same trace_id → skipped
    r2 = client.post("/api/traces", json=_ingest_payload())
    assert r2.json() == {"ingested": 0, "skipped": 1}


def test_export_excludes_synced_until_requested(client):
    client.post("/api/traces", json=_ingest_payload(trace_id="t-export"))
    # ingested traces are marked synced=True, so default export hides them
    default = client.get("/api/traces/export").json()
    assert all(s["trace_id"] != "t-export" for s in default["spans"])
    full = client.get("/api/traces/export", params={"include_synced": True}).json()
    assert any(s["trace_id"] == "t-export" for s in full["spans"])
    assert full["spans"][0]["attributes"]["openinference.span.kind"] == "LLM"


def test_list_traces_filters(client):
    client.post("/api/traces", json=_ingest_payload(trace_id="t-list"))
    rows = client.get("/api/traces", params={"route": "medical_query"}).json()
    assert any(t["trace_id"] == "t-list" for t in rows)
    none = client.get("/api/traces", params={"route": "does-not-exist"}).json()
    assert none == []


# ── Eval (LLM-as-judge) ─────────────────────────────────────────────────────────

def test_evaluate_trace_parses_verdict(db, monkeypatch):
    monkeypatch.setattr(
        fleet_mechanic, "_gemini_json",
        lambda system, prompt: {"label": "unsafe", "score": 0.1, "explanation": "Dose not in excerpts."},
    )
    trace = AITrace(route="medical_query", model_role="medical", model_name="m",
                    system_prompt="s", user_prompt="u", output_text="give 5000mg aspirin")
    db.add(trace); db.commit()
    verdict = fleet_mechanic.evaluate_trace(trace)
    assert verdict["label"] == "unsafe"
    assert verdict["score"] == 0.1


def test_evaluate_trace_fails_closed_on_garbage(db, monkeypatch):
    monkeypatch.setattr(fleet_mechanic, "_gemini_json", lambda s, p: {"label": "lgtm", "score": "n/a"})
    trace = AITrace(route="chat", model_role="medical", model_name="m", output_text="x")
    db.add(trace); db.commit()
    verdict = fleet_mechanic.evaluate_trace(trace)
    assert verdict["label"] == "unsupported"  # off-rubric → fail closed
    assert verdict["score"] == 0.0


def test_parse_json_handles_code_fences():
    assert fleet_mechanic._parse_json('```json\n{"label": "correct"}\n```')["label"] == "correct"
    assert fleet_mechanic._parse_json('garbage {"a": 1} trailing')["a"] == 1
    assert fleet_mechanic._parse_json("not json") == {}


# ── Full run: eval + patch queue ─────────────────────────────────────────────────

def test_run_fleet_mechanic_queues_patch_for_unsafe(db, monkeypatch):
    # an unsafe trace and a correct trace, both synced & unevaluated
    bad = AITrace(trace_id="bad", route="medical_query", model_role="medical",
                  model_name="m", system_prompt="SYS", output_text="give 5000mg aspirin",
                  synced=True, eval_label="unevaluated")
    good = AITrace(trace_id="good", route="medical_query", model_role="medical",
                   model_name="m", system_prompt="SYS", output_text="apply pressure",
                   synced=True, eval_label="unevaluated")
    db.add_all([bad, good]); db.commit()

    def fake_judge(system, prompt):
        if "5000mg" in prompt:
            return {"label": "unsafe", "score": 0.05, "explanation": "Overdose."}
        return {"label": "correct", "score": 0.95, "explanation": "Grounded."}

    def fake_patch(system, prompt):
        return {"failure_summary": "Recommended an aspirin overdose.",
                "proposed_patch": "Never state a dosage that is not present in the provided excerpts.",
                "rationale": "Prevents fabricated dosages."}

    monkeypatch.setattr(fleet_mechanic, "_gemini_json", fake_judge)

    # draft_prompt_patch also calls _gemini_json; route patch calls separately
    real_evaluate = fleet_mechanic.evaluate_trace

    def gemini_dispatch(system, prompt):
        if system == fleet_mechanic._PATCH_SYSTEM:
            return fake_patch(system, prompt)
        return fake_judge(system, prompt)

    monkeypatch.setattr(fleet_mechanic, "_gemini_json", gemini_dispatch)

    summary = fleet_mechanic.run_fleet_mechanic(db, upload_to_arize=False)
    assert summary["evaluated"] == 2
    assert summary["labels"]["unsafe"] == 1
    assert summary["labels"]["correct"] == 1
    assert summary["patches_queued"] == 1

    db.refresh(bad); db.refresh(good)
    assert bad.eval_label == "unsafe"
    assert good.eval_label == "correct"

    patch = db.query(PromptPatch).filter(PromptPatch.trace_id == "bad").first()
    assert patch is not None
    assert patch.status == "queued"
    assert "dosage" in patch.proposed_patch.lower()


def test_run_fleet_mechanic_is_idempotent(db, monkeypatch):
    monkeypatch.setattr(fleet_mechanic, "_gemini_json",
                        lambda s, p: {"label": "correct", "score": 1.0, "explanation": "ok"})
    t = AITrace(trace_id="once", route="chat", model_role="medical", model_name="m",
                output_text="ok", synced=True, eval_label="unevaluated")
    db.add(t); db.commit()
    first = fleet_mechanic.run_fleet_mechanic(db, upload_to_arize=False)
    second = fleet_mechanic.run_fleet_mechanic(db, upload_to_arize=False)
    assert first["evaluated"] == 1
    assert second["evaluated"] == 0  # already evaluated → skipped


# ── Patch lifecycle endpoints ─────────────────────────────────────────────────────

def test_patch_pending_ack_and_reject(client, db):
    trace = AITrace(trace_id="pt", route="medical_query", model_role="medical",
                    model_name="m", output_text="x", synced=True)
    db.add(trace)
    db.add(PromptPatch(patch_id="p-queued", trace_id="pt", target_route="medical_query",
                       target_model_role="medical", proposed_patch="do X", status="queued"))
    db.add(PromptPatch(patch_id="p-draft", trace_id="pt", target_route="medical_query",
                       target_model_role="medical", proposed_patch="do Y", status="drafted"))
    db.commit()

    pending = client.get("/api/traces/patches/pending").json()
    assert {p["patch_id"] for p in pending} == {"p-queued"}

    acked = client.post("/api/traces/patches/p-queued/ack").json()
    assert acked["status"] == "pushed" and acked["pushed_at"]

    rejected = client.post("/api/traces/patches/p-draft/reject").json()
    assert rejected["status"] == "rejected"

    assert client.post("/api/traces/patches/missing/ack").status_code == 404


# ── Arize availability ────────────────────────────────────────────────────────────

def test_arize_unavailable_without_creds():
    # No ARIZE_SPACE_ID / ARIZE_API_KEY in the test env.
    assert arize_client.is_available() is False
    assert arize_client.get_tracer() is None
    # replay is a no-op that reports nothing sent
    assert arize_client.replay_traces([]) == 0
