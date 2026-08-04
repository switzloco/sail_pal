"""Firestore store — the hosted deployment's durable database.

Layout:

    vessels/{vessel_id}
        name, imo_number, created_at
        members:     { "<uid>": "owner" | "editor" | "viewer" }
        member_uids: [ "<uid>", ... ]        # for array_contains lookups
      crew/{crew_id}
      components/{component_id}
      health_events/{event_id}
      maintenance_logs/{log_id}

Sub-collections rather than top-level collections with a `vessel_id` field: it
keeps a boat's data in one subtree, so sharing, exporting or deleting a vessel
is one operation rather than five fan-out queries.

`members` is a map for cheap role lookups; `member_uids` duplicates the keys as
an array because Firestore cannot query map keys but can `array_contains`. They
are written together and must stay in sync.

Filtering happens server-side only for single-field equality, which Firestore
serves from automatic indexes. Ordering is done in Python: combining a filter
with an order_by needs a hand-built composite index per query shape, and a
vessel holds tens of documents, not millions. If a boat ever accumulates enough
history for that to hurt, add the composite indexes and push the sort down.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Iterable, Optional

from backend.store.base import (
    ROLE_EDITOR,
    ROLE_OWNER,
    CollectionSpec,
    StoreError,
    Vessel,
    VesselNotFound,
    VesselStore,
    spec_for,
)

VESSELS = "vessels"


def _encode(data: dict[str, Any], spec: CollectionSpec) -> dict[str, Any]:
    """Python values -> Firestore values.

    Lists and dicts go in natively. Firestore has no date-only type, so dates
    round-trip as ISO-8601 strings, which pydantic parses straight back.
    """
    out = dict(data)
    for field in spec.date_fields:
        value = out.get(field)
        if isinstance(value, datetime):
            out[field] = value.date().isoformat()
        elif isinstance(value, date):
            out[field] = value.isoformat()
    return out


class FirestoreStore(VesselStore):
    def __init__(self, client: Any):
        self.client = client

    # ── Vessels ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_vessel(doc_id: str, data: dict[str, Any]) -> Vessel:
        return Vessel(
            vessel_id=doc_id,
            name=data.get("name", ""),
            imo_number=data.get("imo_number"),
            created_at=data.get("created_at"),
            members=dict(data.get("members") or {}),
        )

    def get_vessel(self, vessel_id: str) -> Optional[Vessel]:
        snap = self.client.collection(VESSELS).document(vessel_id).get()
        if not snap.exists:
            return None
        return self._to_vessel(snap.id, snap.to_dict() or {})

    def list_vessels_for_user(self, uid: Optional[str]) -> list[Vessel]:
        if uid is None:
            return []
        query = self.client.collection(VESSELS).where("member_uids", "array_contains", uid)
        vessels = [self._to_vessel(s.id, s.to_dict() or {}) for s in query.stream()]
        vessels.sort(key=lambda v: _sort_key(v.created_at), reverse=True)
        return vessels

    def create_vessel(
        self,
        name: str,
        imo_number: Optional[str] = None,
        owner_uid: Optional[str] = None,
        vessel_id: Optional[str] = None,
    ) -> Vessel:
        vessel_id = vessel_id or str(uuid.uuid4())
        members = {owner_uid: ROLE_OWNER} if owner_uid else {}
        payload = {
            "name": name,
            "imo_number": imo_number,
            "created_at": datetime.utcnow(),
            "members": members,
            "member_uids": list(members),
        }
        self.client.collection(VESSELS).document(vessel_id).set(payload)
        return self._to_vessel(vessel_id, payload)

    def update_vessel(self, vessel_id: str, data: dict[str, Any]) -> Vessel:
        ref = self.client.collection(VESSELS).document(vessel_id)
        if not ref.get().exists:
            raise VesselNotFound(vessel_id)
        # Membership is only ever changed through add_member/remove_member, so
        # a stray field in an update payload can't hand someone else access.
        patch = {
            k: v
            for k, v in data.items()
            if v is not None and k not in ("members", "member_uids", "vessel_id")
        }
        if patch:
            ref.update(patch)
        return self.get_vessel(vessel_id)  # type: ignore[return-value]

    # ── Membership ───────────────────────────────────────────────────────────

    def _write_members(self, vessel_id: str, members: dict[str, str]) -> Vessel:
        self.client.collection(VESSELS).document(vessel_id).update(
            {"members": members, "member_uids": list(members)}
        )
        return self.get_vessel(vessel_id)  # type: ignore[return-value]

    def add_member(self, vessel_id: str, uid: str, role: str = ROLE_EDITOR) -> Vessel:
        vessel = self.get_vessel(vessel_id)
        if not vessel:
            raise VesselNotFound(vessel_id)
        members = dict(vessel.members)
        members[uid] = role
        return self._write_members(vessel_id, members)

    def remove_member(self, vessel_id: str, uid: str) -> Vessel:
        vessel = self.get_vessel(vessel_id)
        if not vessel:
            raise VesselNotFound(vessel_id)
        members = dict(vessel.members)
        if members.get(uid) == ROLE_OWNER and sum(
            1 for r in members.values() if r == ROLE_OWNER
        ) == 1:
            raise StoreError("Cannot remove the last owner of a vessel")
        members.pop(uid, None)
        return self._write_members(vessel_id, members)

    # ── Documents ────────────────────────────────────────────────────────────

    def _collection(self, vessel_id: str, collection: str):
        return (
            self.client.collection(VESSELS)
            .document(vessel_id)
            .collection(collection)
        )

    def list_docs(
        self,
        vessel_id: str,
        collection: str,
        *,
        where: Iterable[tuple[str, Any]] = (),
        order_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        spec = spec_for(collection)
        query = self._collection(vessel_id, collection)
        for field, value in where:
            query = query.where(field, "==", value)

        docs = [s.to_dict() or {} for s in query.stream()]

        order_field = order_by or spec.default_order
        if order_field:
            desc = spec.default_descending if descending is None else descending
            docs.sort(key=lambda d: _sort_key(d.get(order_field)), reverse=desc)
        return docs

    def get_doc(self, vessel_id: str, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        snap = self._collection(vessel_id, collection).document(doc_id).get()
        return (snap.to_dict() or {}) if snap.exists else None

    def create_doc(
        self, vessel_id: str, collection: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        spec = spec_for(collection)
        payload = _encode(data, spec)
        payload["vessel_id"] = vessel_id
        payload.setdefault(spec.id_field, str(uuid.uuid4()))
        payload.setdefault("created_at", datetime.utcnow())
        self._collection(vessel_id, collection).document(payload[spec.id_field]).set(payload)
        return payload

    def update_doc(
        self, vessel_id: str, collection: str, doc_id: str, data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        spec = spec_for(collection)
        ref = self._collection(vessel_id, collection).document(doc_id)
        if not ref.get().exists:
            return None
        patch = {
            k: v
            for k, v in _encode(data, spec).items()
            if k not in (spec.id_field, "vessel_id")
        }
        if patch:
            ref.update(patch)
        return self.get_doc(vessel_id, collection, doc_id)

    def delete_doc(self, vessel_id: str, collection: str, doc_id: str) -> bool:
        ref = self._collection(vessel_id, collection).document(doc_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


def _sort_key(value: Any) -> Any:
    """Total order across mixed/missing values so sorting never raises.

    Firestore documents are schemaless — an older record may be missing the
    field entirely, and comparing None to a datetime is a TypeError.
    """
    if value is None:
        return (0, "")
    if isinstance(value, datetime):
        return (1, value.replace(tzinfo=None).isoformat())
    if isinstance(value, date):
        return (1, value.isoformat())
    return (2, str(value).lower())
