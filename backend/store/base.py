"""Storage interface shared by the SQLite and Firestore backends."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from backend.db.models import (
    Component,
    CrewMember,
    HealthEvent,
    MaintenanceLog,
)


class StoreError(Exception):
    """Base class for storage failures the routers should translate to HTTP."""


class PermissionDenied(StoreError):
    """Caller is not a member of the vessel they addressed."""


class VesselNotFound(StoreError):
    """No vessel exists with the given id."""


# ── Membership roles ─────────────────────────────────────────────────────────
# Ordered least to most privileged. Sharing a boat with another user is an
# `add_member` call — the data model does not change.
ROLE_VIEWER = "viewer"
ROLE_EDITOR = "editor"
ROLE_OWNER = "owner"

ROLE_RANK = {ROLE_VIEWER: 0, ROLE_EDITOR: 1, ROLE_OWNER: 2}
ROLES = tuple(ROLE_RANK)


def can_write(role: Optional[str]) -> bool:
    return role is not None and ROLE_RANK.get(role, -1) >= ROLE_RANK[ROLE_EDITOR]


def can_administer(role: Optional[str]) -> bool:
    """Only owners may add or remove other members."""
    return role == ROLE_OWNER


@dataclass(frozen=True)
class CollectionSpec:
    """How one entity is shaped in each backend.

    SQLite stores lists and dicts as JSON strings in TEXT columns (`json_fields`)
    and dates as real DATE columns. Firestore stores lists and maps natively, and
    has no date-only type, so `date_fields` round-trip as ISO-8601 strings.
    """

    name: str
    model: type
    id_field: str
    json_fields: tuple[str, ...] = ()
    date_fields: tuple[str, ...] = ()
    default_order: Optional[str] = None
    default_descending: bool = False


COLLECTIONS: dict[str, CollectionSpec] = {
    spec.name: spec
    for spec in (
        CollectionSpec(
            name="crew",
            model=CrewMember,
            id_field="crew_id",
            json_fields=("allergies", "emergency_contact"),
            date_fields=("date_of_birth",),
            default_order="full_name",
        ),
        CollectionSpec(
            name="components",
            model=Component,
            id_field="component_id",
            json_fields=("spare_parts",),
            date_fields=("install_date",),
            default_order="name",
        ),
        CollectionSpec(
            name="health_events",
            model=HealthEvent,
            id_field="event_id",
            json_fields=("symptoms", "vital_signs", "photo_paths"),
            default_order="event_time",
            default_descending=True,
        ),
        CollectionSpec(
            name="maintenance_logs",
            model=MaintenanceLog,
            id_field="log_id",
            json_fields=("photo_paths", "parts_used"),
            default_order="event_time",
            default_descending=True,
        ),
    )
}


def spec_for(collection: str) -> CollectionSpec:
    try:
        return COLLECTIONS[collection]
    except KeyError:
        raise StoreError(f"Unknown collection: {collection!r}") from None


@dataclass
class Vessel:
    """A vessel plus who can see it. `members` maps uid -> role."""

    vessel_id: str
    name: str
    imo_number: Optional[str] = None
    created_at: Any = None
    members: dict[str, str] = field(default_factory=dict)

    def role_for(self, uid: Optional[str]) -> Optional[str]:
        if uid is None:
            return None
        return self.members.get(uid)

    def as_dict(self) -> dict[str, Any]:
        """Shape the API returns — membership is deliberately not exposed here."""
        return {
            "vessel_id": self.vessel_id,
            "name": self.name,
            "imo_number": self.imo_number,
            "created_at": self.created_at,
        }


class VesselStore(abc.ABC):
    """CRUD over vessels and their sub-collections.

    Implementations must not enforce authorization themselves — the router layer
    resolves the caller's role via `get_vessel` and decides. Keeping that in one
    place means the two backends cannot drift on who may read what.
    """

    # ── Vessels ──────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def get_vessel(self, vessel_id: str) -> Optional[Vessel]:
        ...

    @abc.abstractmethod
    def list_vessels_for_user(self, uid: Optional[str]) -> list[Vessel]:
        """Every vessel `uid` is a member of, newest first."""

    @abc.abstractmethod
    def create_vessel(
        self,
        name: str,
        imo_number: Optional[str] = None,
        owner_uid: Optional[str] = None,
        vessel_id: Optional[str] = None,
    ) -> Vessel:
        ...

    @abc.abstractmethod
    def update_vessel(self, vessel_id: str, data: dict[str, Any]) -> Vessel:
        ...

    # ── Membership ───────────────────────────────────────────────────────────

    @abc.abstractmethod
    def add_member(self, vessel_id: str, uid: str, role: str = ROLE_EDITOR) -> Vessel:
        ...

    @abc.abstractmethod
    def remove_member(self, vessel_id: str, uid: str) -> Vessel:
        ...

    # ── Documents within a vessel ────────────────────────────────────────────

    @abc.abstractmethod
    def list_docs(
        self,
        vessel_id: str,
        collection: str,
        *,
        where: Iterable[tuple[str, Any]] = (),
        order_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def get_doc(self, vessel_id: str, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def create_doc(
        self, vessel_id: str, collection: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        ...

    @abc.abstractmethod
    def update_doc(
        self, vessel_id: str, collection: str, doc_id: str, data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        ...

    @abc.abstractmethod
    def delete_doc(self, vessel_id: str, collection: str, doc_id: str) -> bool:
        ...
