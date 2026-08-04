"""
Tests for chat model routing, inventory grounding, and prompt hygiene.

These cover the two things the pared-back app leans on hardest: picking the
right model for a turn, and never leaving the crew with a bare refusal.
"""
import json

import pytest

from backend.ai import mode_state
from backend.ai.prompt_templates import (
    CITATION_INSTRUCTIONS,
    ENGINE_SYSTEM,
    GENERAL_SYSTEM,
    INVENTORY_GROUNDING,
    MEDICAL_SYSTEM,
)
from backend.routers.ai import (
    MODEL_CHOICES,
    _has_general_intent,
    _has_medical_intent,
    _inventory_context,
    _spare_parts_list,
)


# ── Prompt hygiene ───────────────────────────────────────────────────────────

def test_citation_instructions_do_not_teach_a_dead_end_refusal():
    """The old prompt told the model to answer 'I do not have information on
    that in my current library' and stop, which is what crew kept hitting."""
    assert "I do not have information on that in my current library" not in CITATION_INSTRUCTIONS
    assert "STILL ANSWER" in CITATION_INSTRUCTIONS


def test_citation_instructions_still_forbid_invented_dosages():
    lowered = CITATION_INSTRUCTIONS.lower()
    assert "never state a specific drug dosage" in lowered
    assert "torque value" in lowered


def test_medical_system_requires_actionable_fallback():
    assert "Never refuse to engage with a symptom" in MEDICAL_SYSTEM


def test_general_system_names_the_two_pillars():
    assert "MEDICAL" in GENERAL_SYSTEM
    assert "INVENTORY" in GENERAL_SYSTEM


def test_engine_system_covers_inventory():
    assert "inventory" in ENGINE_SYSTEM.lower()


# ── Intent classification ────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "crew member has chest pain",
    "how do I treat a deep laceration",
    "what dose of antibiotic for an infected wound",
])
def test_medical_intent_detected(text):
    assert _has_medical_intent(text)


@pytest.mark.parametrize("text", [
    "do we have a spare impeller in stock",
    "what is the service interval on the generator",
    "check the part number for the fuel filter",
])
def test_general_intent_detected(text):
    assert _has_general_intent(text)


def test_generic_words_do_not_trigger_general_intent():
    """'on board' appears in medical questions constantly and must not demote."""
    assert not _has_general_intent("a crew member on board has a fever")


def test_medical_intent_wins_when_both_signals_present():
    text = "what's in the medical stores inventory for a crew member with chest pain"
    assert _has_medical_intent(text)
    assert _has_general_intent(text)


# ── Spare parts parsing ──────────────────────────────────────────────────────

def test_spare_parts_list_parses_json_string():
    assert _spare_parts_list(json.dumps(["impeller", "belt"])) == ["impeller", "belt"]


def test_spare_parts_list_passes_through_decoded_list():
    assert _spare_parts_list(["impeller"]) == ["impeller"]


@pytest.mark.parametrize("raw", [None, "", "not json", json.dumps({"a": 1})])
def test_spare_parts_list_handles_garbage(raw):
    assert _spare_parts_list(raw) == []


# ── Inventory context ────────────────────────────────────────────────────────

def test_inventory_context_empty_without_components(db):
    assert _inventory_context(db) == []


def test_inventory_context_lists_component_and_spares(db, seed_component):
    seed_component.spare_parts = json.dumps(["fuel filter", "impeller"])
    db.commit()

    lines = _inventory_context(db)
    body = "\n".join(lines)

    assert "Vessel inventory on board" in lines[0]
    assert "Main Engine (propulsion)" in body
    assert "MAN B&W 6S50MC-C" in body
    assert "stowed Engine Room" in body
    assert "spares: fuel filter, impeller" in body


def test_inventory_context_marks_missing_spares(db, seed_component):
    body = "\n".join(_inventory_context(db))
    assert "no spares recorded" in body


def test_inventory_context_skips_inactive_components(db, seed_component):
    seed_component.is_active = False
    db.commit()
    assert _inventory_context(db) == []


def test_inventory_context_respects_limit(db, seed_vessel):
    from backend.db.models import Component

    db.add_all([
        Component(
            component_id=f"comp-bulk-{i}",
            vessel_id=seed_vessel.vessel_id,
            name=f"Pump {i}",
            system="propulsion",
        )
        for i in range(10)
    ])
    db.commit()

    lines = _inventory_context(db, limit=3)
    assert len(lines) == 4  # header + 3 components


def test_inventory_grounding_prompt_is_authoritative():
    assert "authoritative record" in INVENTORY_GROUNDING


# ── /api/ai/models ───────────────────────────────────────────────────────────

def test_models_endpoint_lists_the_three_choices(client):
    body = client.get("/api/ai/models").json()
    assert [o["id"] for o in body["options"]] == list(MODEL_CHOICES)
    assert body["mode"] == "local"
    assert isinstance(body["fine_tune_installed"], bool)


def test_models_endpoint_every_option_has_a_hint(client):
    for option in client.get("/api/ai/models").json()["options"]:
        assert option["hint"]
        assert option["label"]


def test_models_endpoint_reports_cloud_mode(client):
    original = mode_state.get_mode()
    mode_state.set_mode("cloud")
    try:
        body = client.get("/api/ai/models").json()
        assert body["mode"] == "cloud"
        # In cloud mode both routes are served by the same hosted model.
        by_id = {o["id"]: o for o in body["options"]}
        assert by_id["medical"]["model"] == by_id["general"]["model"]
    finally:
        mode_state.set_mode(original)
