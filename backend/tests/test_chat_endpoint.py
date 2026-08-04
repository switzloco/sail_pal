"""
End-to-end tests for POST /api/ai/chat.

These capture the system prompt actually handed to the model, which is the
only way to prove the two behaviours the pared-back app depends on: the
inventory is in front of the model, and nothing instructs it to refuse.
"""
import json
from unittest.mock import patch

import pytest

from backend.config import settings


class _FakeRAG:
    """Stand-in for the FTS5 engine so tests don't touch the knowledge index."""

    def __init__(self, results=None):
        self.results = results or []
        self.queries = []

    def query(self, collection, text, k=3):
        self.queries.append((collection, text, k))
        return self.results


@pytest.fixture(autouse=True)
def _vessel(seed_vessel):
    """Every chat turn resolves against a vessel; give the suite a real one.

    Without this the request would mint an empty vessel on the fly, which is
    correct behaviour but hides the seeded crew and components these tests need.
    """
    return seed_vessel


@pytest.fixture()
def captured():
    """Run a chat turn against a stubbed LLM and capture the prompt it got."""
    calls = []

    async def _fake_tokens(system, user_prompt, images=None, severity="minor", model_override=None):
        calls.append({
            "system": system,
            "user_prompt": user_prompt,
            "model_override": model_override,
        })
        yield "ok"

    def _run(client, payload, rag=None):
        calls.clear()
        with patch("backend.routers.ai._llm_tokens", _fake_tokens), \
             patch("backend.routers.ai.get_rag_engine", return_value=rag or _FakeRAG()):
            response = client.post("/api/ai/chat", json=payload)
        assert response.status_code == 200
        # Drain the stream so the generator actually runs.
        body = response.text
        assert calls, "the LLM was never called"
        return calls[0], body

    return _run


def _ask(text, **extra):
    return {"messages": [{"role": "user", "content": text}], **extra}


# ── The regression this whole change exists to fix ───────────────────────────

def test_grounded_turn_never_instructs_a_dead_end_refusal(client, captured, seed_component):
    """With RAG hits present, the old prompt told the model to answer
    'I do not have information on that in my current library' and stop."""
    rag = _FakeRAG([{"text": "Constipation is treated with…", "metadata": {"source": "WHO IMGS", "page": 210}}])
    call, _ = captured(client, _ask("crew member hasn't had a bowel movement in 2 days"), rag=rag)

    assert "I do not have information on that in my current library" not in call["system"]
    assert "STILL ANSWER" in call["system"]


def test_grounded_turn_still_bans_invented_dosages(client, captured):
    rag = _FakeRAG([{"text": "Give 500 mg…", "metadata": {"source": "WHO IMGS", "page": 41}}])
    call, _ = captured(client, _ask("what antibiotic for an infected wound"), rag=rag)
    assert "never state a specific drug dosage" in call["system"].lower()


# ── Model selection ──────────────────────────────────────────────────────────

def test_auto_routes_medical_question_to_medical_model(client, captured):
    call, _ = captured(client, _ask("crew member has chest pain"))
    assert call["model_override"] == settings.effective_medical_model


def test_auto_routes_spares_question_to_general_model(client, captured):
    call, _ = captured(client, _ask("do we have a spare impeller in stock?"))
    assert call["model_override"] is None


def test_explicit_medical_choice_overrides_the_router(client, captured):
    call, _ = captured(client, _ask("what is the service interval on the generator", model_choice="medical"))
    assert call["model_override"] == settings.effective_medical_model


def test_explicit_general_choice_overrides_the_router(client, captured):
    call, _ = captured(client, _ask("crew member has chest pain", model_choice="general"))
    assert call["model_override"] is None


def test_explicit_general_choice_overrides_crew_context(client, captured, seed_crew):
    call, _ = captured(client, _ask("what spares do we hold", crew_id="crew-1", model_choice="general"))
    assert call["model_override"] is None


def test_unknown_model_choice_falls_back_to_auto(client, captured):
    call, _ = captured(client, _ask("crew member has chest pain", model_choice="nonsense"))
    assert call["model_override"] == settings.effective_medical_model


def test_response_stream_announces_the_route(client, captured):
    _, body = captured(client, _ask("do we have a spare impeller in stock?"))
    assert '"route": "general"' in body


def test_medical_route_announced_for_clinical_question(client, captured):
    _, body = captured(client, _ask("crew member has chest pain"))
    assert '"route": "medical"' in body


def test_clinical_signal_beats_inventory_wording(client, captured):
    """'what's in the medical stores for chest pain' is a medical turn."""
    call, _ = captured(client, _ask("what's in the medical inventory for chest pain?"))
    assert call["model_override"] == settings.effective_medical_model


# ── Inventory awareness ──────────────────────────────────────────────────────

def test_inventory_is_injected_into_every_turn(client, captured, seed_component, db):
    seed_component.spare_parts = json.dumps(["fuel filter", "impeller"])
    db.commit()

    call, _ = captured(client, _ask("do we have a spare impeller?"))

    assert "Vessel inventory on board" in call["system"]
    assert "Main Engine (propulsion)" in call["system"]
    assert "spares: fuel filter, impeller" in call["system"]
    assert "authoritative record" in call["system"]


def test_inventory_reaches_medical_turns_too(client, captured, seed_component):
    call, _ = captured(client, _ask("crew member has chest pain"))
    assert "Vessel inventory on board" in call["system"]


def test_no_inventory_block_when_nothing_is_recorded(client, captured):
    call, _ = captured(client, _ask("crew member has chest pain"))
    assert "Vessel inventory on board" not in call["system"]
    assert "authoritative record" not in call["system"]


def test_general_turns_query_the_technical_manuals(client, captured):
    rag = _FakeRAG()
    captured(client, _ask("do we have a spare impeller in stock?"), rag=rag)
    assert ("engine_manuals", "do we have a spare impeller in stock?", 2) in rag.queries


def test_medical_turns_query_the_who_protocols(client, captured):
    rag = _FakeRAG()
    captured(client, _ask("crew member has chest pain"), rag=rag)
    assert ("medical_protocols", "crew member has chest pain", 3) in rag.queries


# ── Context grounding still works ────────────────────────────────────────────

def test_crew_context_carries_allergies_into_the_prompt(client, captured, seed_crew):
    call, _ = captured(client, _ask("is this rash a concern?", crew_id="crew-1"))
    assert "John Smith" in call["system"]
    assert "Penicillin" in call["system"]


def test_component_context_selects_the_engineering_prompt(client, captured, seed_component):
    call, _ = captured(client, _ask("it is vibrating", component_id="comp-1"))
    assert "Main Engine" in call["system"]
    assert call["model_override"] is None
