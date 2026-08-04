"""Hosted-mode auth: who can reach which boat.

The hosted app is on the public internet holding real crew medical records, so
these are the tests that matter most. They run against the Firestore store,
since that is the only backend that has membership at all.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.auth import current_user
from backend.config import settings
from backend.main import app
from backend.store import get_store
from backend.store.base import ROLE_EDITOR, ROLE_OWNER, ROLE_VIEWER, StoreError
from backend.store.firestore_store import FirestoreStore
from backend.tests.fake_firestore import FakeFirestore

NICK = "uid-nick"
CHRIS = "uid-chris"
STRANGER = "uid-stranger"

TOKENS = {
    "nick-token": {"uid": NICK, "email": "nick@example.com"},
    "chris-token": {"uid": CHRIS, "email": "chris@example.com"},
    "stranger-token": {"uid": STRANGER, "email": "stranger@example.com"},
}


@pytest.fixture()
def store():
    return FirestoreStore(FakeFirestore())


@pytest.fixture()
def hosted(store):
    """A TestClient behaving like the Cloud Run deployment: auth required."""
    app.dependency_overrides[get_store] = lambda: store
    # current_user is resolved per-request from the header, so only the flag
    # needs flipping — the real verification path stays under test.
    original = settings.require_auth
    settings.require_auth = True

    def _verify(token):
        if token not in TOKENS:
            raise ValueError("bad token")
        return TOKENS[token]

    with patch("backend.auth._verify_id_token", side_effect=_verify):
        yield TestClient(app)

    settings.require_auth = original
    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(current_user, None)


def _as(client, token, **kwargs):
    headers = {"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
    return headers


# ── Authentication ───────────────────────────────────────────────────────────

def test_data_route_requires_a_token(hosted):
    assert hosted.get("/api/crew").status_code == 401


def test_garbage_token_is_rejected(hosted):
    r = hosted.get("/api/crew", headers=_as(hosted, "not-a-real-token"))
    assert r.status_code == 401


def test_malformed_authorization_header_is_rejected(hosted):
    r = hosted.get("/api/crew", headers={"Authorization": "nick-token"})
    assert r.status_code == 401


def test_valid_token_gets_through(hosted):
    r = hosted.get("/api/crew", headers=_as(hosted, "nick-token"))
    assert r.status_code == 200


def test_local_mode_needs_no_token(client):
    """Desktop mode is scoped by physical access to the laptop, not accounts."""
    assert client.get("/api/crew").status_code == 200


# ── First run ────────────────────────────────────────────────────────────────

def test_first_request_mints_a_vessel(hosted, store):
    r = hosted.get("/api/setup/vessel-info", headers=_as(hosted, "nick-token"))
    assert r.status_code == 200
    assert r.json()["name"] == "My Vessel"
    assert len(store.list_vessels_for_user(NICK)) == 1


def test_the_minting_user_becomes_owner(hosted, store):
    hosted.get("/api/setup/vessel-info", headers=_as(hosted, "nick-token"))
    vessel = store.list_vessels_for_user(NICK)[0]
    assert vessel.members[NICK] == ROLE_OWNER


def test_a_second_request_reuses_the_same_vessel(hosted, store):
    first = hosted.get("/api/setup/vessel-info", headers=_as(hosted, "nick-token")).json()
    second = hosted.get("/api/setup/vessel-info", headers=_as(hosted, "nick-token")).json()
    assert first["vessel_id"] == second["vessel_id"]


def test_users_get_separate_vessels(hosted, store):
    nick = hosted.get("/api/setup/vessel-info", headers=_as(hosted, "nick-token")).json()
    chris = hosted.get("/api/setup/vessel-info", headers=_as(hosted, "chris-token")).json()
    assert nick["vessel_id"] != chris["vessel_id"]


# ── Isolation ────────────────────────────────────────────────────────────────

def test_crew_written_by_one_user_is_invisible_to_another(hosted):
    hosted.post(
        "/api/crew",
        headers=_as(hosted, "nick-token"),
        json={"vessel_id": "ignored", "full_name": "Nick", "role": "Skipper"},
    )
    mine = hosted.get("/api/crew", headers=_as(hosted, "nick-token")).json()
    theirs = hosted.get("/api/crew", headers=_as(hosted, "chris-token")).json()

    assert [c["full_name"] for c in mine] == ["Nick"]
    assert theirs == []


def test_naming_someone_elses_vessel_id_is_a_404(hosted, store):
    nick_vessel = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]

    r = hosted.get(
        "/api/crew",
        headers={**_as(hosted, "stranger-token"), "X-Vessel-Id": nick_vessel},
    )
    # 404 rather than 403 so probing cannot distinguish a real boat from a fake one.
    assert r.status_code == 404


def test_body_vessel_id_cannot_redirect_a_write(hosted, store):
    """A client must not be able to write into another boat by naming it."""
    nick_vessel = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    hosted.get("/api/setup/vessel-info", headers=_as(hosted, "chris-token"))

    hosted.post(
        "/api/crew",
        headers=_as(hosted, "chris-token"),
        json={"vessel_id": nick_vessel, "full_name": "Trojan", "role": "Deckhand"},
    )

    nick_crew = hosted.get("/api/crew", headers=_as(hosted, "nick-token")).json()
    assert nick_crew == []


# ── Sharing ──────────────────────────────────────────────────────────────────

def test_owner_can_share_a_boat(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_EDITOR)

    r = hosted.get("/api/crew", headers={**_as(hosted, "chris-token"), "X-Vessel-Id": vessel_id})
    assert r.status_code == 200


def test_shared_editor_can_write(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_EDITOR)

    r = hosted.post(
        "/api/crew",
        headers={**_as(hosted, "chris-token"), "X-Vessel-Id": vessel_id},
        json={"vessel_id": vessel_id, "full_name": "Added by Chris", "role": "Mate"},
    )
    assert r.status_code == 201


def test_shared_viewer_cannot_write(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_VIEWER)

    read = hosted.get("/api/crew", headers={**_as(hosted, "chris-token"), "X-Vessel-Id": vessel_id})
    write = hosted.post(
        "/api/crew",
        headers={**_as(hosted, "chris-token"), "X-Vessel-Id": vessel_id},
        json={"vessel_id": vessel_id, "full_name": "Nope", "role": "Mate"},
    )
    assert read.status_code == 200
    assert write.status_code == 403


def test_editor_cannot_change_membership(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_EDITOR)

    r = hosted.delete(
        f"/api/vessels/{vessel_id}/members/{NICK}",
        headers=_as(hosted, "chris-token"),
    )
    assert r.status_code == 403


def test_owner_sees_the_member_list(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_EDITOR)

    with patch("backend.routers.vessels._email_for", return_value=None):
        members = hosted.get(
            f"/api/vessels/{vessel_id}/members", headers=_as(hosted, "nick-token")
        ).json()

    by_uid = {m["uid"]: m for m in members}
    assert by_uid[NICK]["role"] == ROLE_OWNER
    assert by_uid[NICK]["is_you"] is True
    assert by_uid[CHRIS]["role"] == ROLE_EDITOR


def test_removing_a_member_revokes_access(hosted, store):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    store.add_member(vessel_id, CHRIS, ROLE_EDITOR)

    with patch("backend.routers.vessels._email_for", return_value=None):
        hosted.delete(
            f"/api/vessels/{vessel_id}/members/{CHRIS}", headers=_as(hosted, "nick-token")
        )

    r = hosted.get("/api/crew", headers={**_as(hosted, "chris-token"), "X-Vessel-Id": vessel_id})
    assert r.status_code == 404


def test_the_last_owner_cannot_be_removed(store):
    """Otherwise a boat becomes permanently unadministrable."""
    vessel = store.create_vessel(name="SV Wanderer", owner_uid=NICK)
    with pytest.raises(StoreError):
        store.remove_member(vessel.vessel_id, NICK)


def test_inviting_an_unknown_email_is_a_clear_404(hosted):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]

    with patch("backend.routers.vessels._uid_for_email", return_value=None):
        r = hosted.post(
            f"/api/vessels/{vessel_id}/members",
            headers=_as(hosted, "nick-token"),
            json={"email": "nobody@example.com"},
        )
    assert r.status_code == 404
    assert "sign in once first" in r.json()["detail"]


def test_invite_rejects_an_unknown_role(hosted):
    vessel_id = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]

    r = hosted.post(
        f"/api/vessels/{vessel_id}/members",
        headers=_as(hosted, "nick-token"),
        json={"email": "chris@example.com", "role": "admiral"},
    )
    assert r.status_code == 400


def test_vessel_list_shows_shared_boats(hosted, store):
    nick_vessel = hosted.get(
        "/api/setup/vessel-info", headers=_as(hosted, "nick-token")
    ).json()["vessel_id"]
    hosted.get("/api/setup/vessel-info", headers=_as(hosted, "chris-token"))
    store.add_member(nick_vessel, CHRIS, ROLE_EDITOR)

    mine = hosted.get("/api/vessels", headers=_as(hosted, "chris-token")).json()
    assert nick_vessel in [v["vessel_id"] for v in mine]
    assert len(mine) == 2  # their own boat plus Nick's
