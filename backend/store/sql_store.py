"""SQLite/SQLAlchemy store — the desktop companion's local database.

This is the offline path. It keeps the existing schema exactly as it was: lists
and dicts stay JSON-encoded in TEXT columns, dates stay real DATE columns.

Membership is not modelled here. The local database lives on one person's
laptop, physically scoped to whoever can open the lid, so `get_vessel` reports
every caller as the owner. The router layer skips auth entirely in local mode.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from backend.db.models import Vessel as VesselRow
from backend.store.base import (
    ROLE_OWNER,
    CollectionSpec,
    Vessel,
    VesselNotFound,
    VesselStore,
    spec_for,
)


def _encode(data: dict[str, Any], spec: CollectionSpec) -> dict[str, Any]:
    """Python values -> column values (lists/dicts become JSON strings)."""
    out = dict(data)
    for field in spec.json_fields:
        if field in out and not isinstance(out[field], (str, type(None))):
            out[field] = json.dumps(out[field])
    return out


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


class SqlStore(VesselStore):
    def __init__(self, db: Session):
        self.db = db

    # ── Vessels ──────────────────────────────────────────────────────────────

    def _to_vessel(self, row: VesselRow) -> Vessel:
        return Vessel(
            vessel_id=row.vessel_id,
            name=row.name,
            imo_number=row.imo_number,
            created_at=row.created_at,
            # Local mode has no accounts; whoever holds the laptop owns the boat.
            members={},
        )

    def get_vessel(self, vessel_id: str) -> Optional[Vessel]:
        row = self.db.query(VesselRow).filter(VesselRow.vessel_id == vessel_id).first()
        return self._to_vessel(row) if row else None

    def list_vessels_for_user(self, uid: Optional[str]) -> list[Vessel]:
        rows = self.db.query(VesselRow).order_by(VesselRow.created_at.desc()).all()
        return [self._to_vessel(r) for r in rows]

    def create_vessel(
        self,
        name: str,
        imo_number: Optional[str] = None,
        owner_uid: Optional[str] = None,
        vessel_id: Optional[str] = None,
    ) -> Vessel:
        row = VesselRow(
            vessel_id=vessel_id or str(uuid.uuid4()),
            name=name,
            imo_number=imo_number,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_vessel(row)

    def update_vessel(self, vessel_id: str, data: dict[str, Any]) -> Vessel:
        row = self.db.query(VesselRow).filter(VesselRow.vessel_id == vessel_id).first()
        if not row:
            raise VesselNotFound(vessel_id)
        for key, value in data.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return self._to_vessel(row)

    # ── Membership (no-ops locally) ──────────────────────────────────────────

    def add_member(self, vessel_id: str, uid: str, role: str = ROLE_OWNER) -> Vessel:
        vessel = self.get_vessel(vessel_id)
        if not vessel:
            raise VesselNotFound(vessel_id)
        return vessel

    def remove_member(self, vessel_id: str, uid: str) -> Vessel:
        vessel = self.get_vessel(vessel_id)
        if not vessel:
            raise VesselNotFound(vessel_id)
        return vessel

    # ── Documents ────────────────────────────────────────────────────────────

    def _query(self, vessel_id: str, spec: CollectionSpec):
        return self.db.query(spec.model).filter(spec.model.vessel_id == vessel_id)

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
        query = self._query(vessel_id, spec)
        for field, value in where:
            query = query.filter(getattr(spec.model, field) == value)

        order_field = order_by or spec.default_order
        if order_field:
            column = getattr(spec.model, order_field)
            desc = spec.default_descending if descending is None else descending
            query = query.order_by(column.desc() if desc else column.asc())

        return [_row_to_dict(row) for row in query.all()]

    def get_doc(self, vessel_id: str, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        spec = spec_for(collection)
        row = (
            self._query(vessel_id, spec)
            .filter(getattr(spec.model, spec.id_field) == doc_id)
            .first()
        )
        return _row_to_dict(row) if row else None

    def create_doc(
        self, vessel_id: str, collection: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        spec = spec_for(collection)
        payload = _encode(data, spec)
        payload["vessel_id"] = vessel_id
        payload.setdefault(spec.id_field, str(uuid.uuid4()))

        columns = {c.name for c in spec.model.__table__.columns}
        row = spec.model(**{k: v for k, v in payload.items() if k in columns})
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _row_to_dict(row)

    def update_doc(
        self, vessel_id: str, collection: str, doc_id: str, data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        spec = spec_for(collection)
        row = (
            self._query(vessel_id, spec)
            .filter(getattr(spec.model, spec.id_field) == doc_id)
            .first()
        )
        if not row:
            return None
        for key, value in _encode(data, spec).items():
            if hasattr(row, key) and key not in (spec.id_field, "vessel_id"):
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return _row_to_dict(row)

    def delete_doc(self, vessel_id: str, collection: str, doc_id: str) -> bool:
        spec = spec_for(collection)
        row = (
            self._query(vessel_id, spec)
            .filter(getattr(spec.model, spec.id_field) == doc_id)
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
