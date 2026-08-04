"""The SQLite and Firestore stores must behave identically.

Every test here runs twice, once per backend. That is the point: the desktop
app and the hosted app share every router above this layer, so any divergence
shows up as a bug on exactly one deployment — the hardest kind to find.
"""
from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from backend.store.base import (
    ROLE_EDITOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    StoreError,
    VesselNotFound,
    can_administer,
    can_write,
)
from backend.store.firestore_store import FirestoreStore
from backend.store.sql_store import SqlStore
from backend.tests.fake_firestore import FakeFirestore


@pytest.fixture(params=["sql", "firestore"])
def store(request, db):
    if request.param == "sql":
        return SqlStore(db)
    return FirestoreStore(FakeFirestore())


@pytest.fixture()
def vessel(store):
    return store.create_vessel(name="SV Wanderer", imo_number="1234567", owner_uid="uid-nick")


# ── Vessels ──────────────────────────────────────────────────────────────────

def test_create_and_read_vessel(store, vessel):
    fetched = store.get_vessel(vessel.vessel_id)
    assert fetched is not None
    assert fetched.name == "SV Wanderer"
    assert fetched.imo_number == "1234567"


def test_get_missing_vessel_returns_none(store):
    assert store.get_vessel("nope") is None


def test_update_vessel_changes_name(store, vessel):
    updated = store.update_vessel(vessel.vessel_id, {"name": "SV Wanderer II"})
    assert updated.name == "SV Wanderer II"
    assert store.get_vessel(vessel.vessel_id).name == "SV Wanderer II"


def test_update_missing_vessel_raises(store):
    with pytest.raises(VesselNotFound):
        store.update_vessel("nope", {"name": "x"})


# ── Documents ────────────────────────────────────────────────────────────────

def test_create_doc_assigns_id_and_vessel(store, vessel):
    doc = store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})
    assert doc["crew_id"]
    assert doc["vessel_id"] == vessel.vessel_id


def test_create_doc_honours_supplied_id(store, vessel):
    doc = store.create_doc(
        vessel.vessel_id, "crew", {"crew_id": "crew-abc", "full_name": "Nick", "role": "Skipper"}
    )
    assert doc["crew_id"] == "crew-abc"
    assert store.get_doc(vessel.vessel_id, "crew", "crew-abc") is not None


def test_get_missing_doc_returns_none(store, vessel):
    assert store.get_doc(vessel.vessel_id, "crew", "nope") is None


def test_update_doc_applies_patch(store, vessel):
    doc = store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})
    updated = store.update_doc(
        vessel.vessel_id, "crew", doc["crew_id"], {"role": "Medical Person in Charge"}
    )
    assert updated["role"] == "Medical Person in Charge"
    assert updated["full_name"] == "Nick"


def test_update_missing_doc_returns_none(store, vessel):
    assert store.update_doc(vessel.vessel_id, "crew", "nope", {"role": "x"}) is None


def test_update_doc_cannot_move_it_to_another_vessel(store, vessel):
    doc = store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})
    updated = store.update_doc(
        vessel.vessel_id, "crew", doc["crew_id"], {"vessel_id": "someone-elses-boat"}
    )
    assert updated["vessel_id"] == vessel.vessel_id


def test_delete_doc(store, vessel):
    doc = store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})
    assert store.delete_doc(vessel.vessel_id, "crew", doc["crew_id"]) is True
    assert store.get_doc(vessel.vessel_id, "crew", doc["crew_id"]) is None


def test_delete_missing_doc_returns_false(store, vessel):
    assert store.delete_doc(vessel.vessel_id, "crew", "nope") is False


def test_docs_are_scoped_to_their_vessel(store):
    mine = store.create_vessel(name="Mine", owner_uid="uid-a")
    theirs = store.create_vessel(name="Theirs", owner_uid="uid-b")
    store.create_doc(mine.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})

    assert len(store.list_docs(mine.vessel_id, "crew")) == 1
    assert store.list_docs(theirs.vessel_id, "crew") == []


def test_list_docs_filters_by_equality(store, vessel):
    store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper", "is_active": True})
    store.create_doc(vessel.vessel_id, "crew", {"full_name": "Gone", "role": "Deckhand", "is_active": False})

    active = store.list_docs(vessel.vessel_id, "crew", where=[("is_active", True)])
    assert [d["full_name"] for d in active] == ["Nick"]


def test_list_docs_uses_the_collection_default_order(store, vessel):
    for name in ("Zoe", "Adam", "Mia"):
        store.create_doc(vessel.vessel_id, "crew", {"full_name": name, "role": "Crew"})
    assert [d["full_name"] for d in store.list_docs(vessel.vessel_id, "crew")] == ["Adam", "Mia", "Zoe"]


def _log_events(store, vessel, days):
    """SQLite enforces the crew foreign key; Firestore has no such concept.
    Creating a real crew member keeps the fixture valid on both backends."""
    crew = store.create_doc(vessel.vessel_id, "crew", {"full_name": "Nick", "role": "Skipper"})
    for day in days:
        store.create_doc(
            vessel.vessel_id,
            "health_events",
            {
                "crew_id": crew["crew_id"],
                "logged_by": crew["crew_id"],
                "severity": "minor",
                "event_time": datetime(2026, 8, day, 12, 0),
            },
        )


def test_health_events_default_to_newest_first(store, vessel):
    _log_events(store, vessel, (3, 1, 2))
    events = store.list_docs(vessel.vessel_id, "health_events")
    assert [e["event_time"].day for e in events] == [3, 2, 1]


def test_explicit_order_overrides_the_default(store, vessel):
    _log_events(store, vessel, (3, 1, 2))
    events = store.list_docs(vessel.vessel_id, "health_events", order_by="event_time", descending=False)
    assert [e["event_time"].day for e in events] == [1, 2, 3]


# ── Field shapes: JSON strings in SQLite, native values in Firestore ─────────

def _as_list(value):
    """Both encodings decode to the same Python list."""
    return json.loads(value) if isinstance(value, str) else value


def test_list_fields_round_trip(store, vessel):
    doc = store.create_doc(
        vessel.vessel_id,
        "crew",
        {"full_name": "Nick", "role": "Skipper", "allergies": ["penicillin", "shellfish"]},
    )
    stored = store.get_doc(vessel.vessel_id, "crew", doc["crew_id"])
    assert _as_list(stored["allergies"]) == ["penicillin", "shellfish"]


def test_dict_fields_round_trip(store, vessel):
    contact = {"name": "Kate", "phone": "555-0100", "relation": "spouse"}
    doc = store.create_doc(
        vessel.vessel_id,
        "crew",
        {"full_name": "Nick", "role": "Skipper", "emergency_contact": contact},
    )
    stored = store.get_doc(vessel.vessel_id, "crew", doc["crew_id"])
    assert _as_list(stored["emergency_contact"]) == contact


def test_spare_parts_round_trip(store, vessel):
    doc = store.create_doc(
        vessel.vessel_id,
        "components",
        {"name": "Main Engine", "system": "propulsion", "spare_parts": ["impeller", "belt"]},
    )
    stored = store.get_doc(vessel.vessel_id, "components", doc["component_id"])
    assert _as_list(stored["spare_parts"]) == ["impeller", "belt"]


def test_date_fields_round_trip(store, vessel):
    doc = store.create_doc(
        vessel.vessel_id,
        "crew",
        {"full_name": "Nick", "role": "Skipper", "date_of_birth": date(1985, 4, 12)},
    )
    stored = store.get_doc(vessel.vessel_id, "crew", doc["crew_id"])
    value = stored["date_of_birth"]
    # SQLite gives back a date; Firestore has no date type, so it gives ISO text.
    assert (value.isoformat() if isinstance(value, date) else value) == "1985-04-12"


def test_read_schema_accepts_both_encodings(store, vessel):
    """The one thing that makes a shared router layer possible."""
    from backend.schemas.pydantic_models import CrewMemberRead

    doc = store.create_doc(
        vessel.vessel_id,
        "crew",
        {
            "full_name": "Nick",
            "role": "Skipper",
            "allergies": ["penicillin"],
            "emergency_contact": {"name": "Kate", "phone": "555-0100", "relation": "spouse"},
            "is_active": True,
        },
    )
    parsed = CrewMemberRead.model_validate(store.get_doc(vessel.vessel_id, "crew", doc["crew_id"]))
    assert parsed.allergies == ["penicillin"]
    assert parsed.emergency_contact["name"] == "Kate"


def test_unknown_collection_is_rejected(store, vessel):
    with pytest.raises(StoreError):
        store.list_docs(vessel.vessel_id, "not_a_collection")


# ── Role helpers ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "role,writable,admin",
    [
        (ROLE_OWNER, True, True),
        (ROLE_EDITOR, True, False),
        (ROLE_VIEWER, False, False),
        (None, False, False),
    ],
)
def test_role_permissions(role, writable, admin):
    assert can_write(role) is writable
    assert can_administer(role) is admin
