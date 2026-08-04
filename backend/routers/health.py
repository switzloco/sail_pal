import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.auth import VesselAccess, active_vessel
from backend.schemas.pydantic_models import HealthEventRead, HealthEventCreate
from backend.store import VesselStore, get_store

router = APIRouter()

COLLECTION = "health_events"


@router.get("/events", response_model=List[HealthEventRead])
def list_health_events(
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    return store.list_docs(access.vessel_id, COLLECTION)


@router.get("/events/{event_id}", response_model=HealthEventRead)
def get_health_event(
    event_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    event = store.get_doc(access.vessel_id, COLLECTION, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Health event not found")
    return event


@router.post("/events", response_model=HealthEventRead, status_code=201)
def create_health_event(
    payload: HealthEventCreate,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    data = payload.model_dump(exclude_unset=True)
    data.pop("vessel_id", None)
    data["event_time"] = payload.event_time or datetime.utcnow()
    data["vital_signs"] = payload.vital_signs.model_dump() if payload.vital_signs else None
    data.setdefault("symptoms", [])
    data.setdefault("photo_paths", [])
    return store.create_doc(access.vessel_id, COLLECTION, data)


@router.get("/crew/{crew_id}/history", response_model=List[HealthEventRead])
def get_crew_health_history(
    crew_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    return store.list_docs(access.vessel_id, COLLECTION, where=[("crew_id", crew_id)])


@router.get("/crew/{crew_id}/vitals-trend")
def get_vitals_trend(
    crew_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    """Time-series of vitals for trend analysis, oldest first."""
    events = store.list_docs(
        access.vessel_id,
        COLLECTION,
        where=[("crew_id", crew_id)],
        order_by="event_time",
        descending=False,
    )

    trend = []
    for event in events:
        vitals = event.get("vital_signs")
        if not vitals:
            continue
        if isinstance(vitals, str):
            try:
                vitals = json.loads(vitals)
            except ValueError:
                continue
        if not isinstance(vitals, dict):
            continue

        event_time = event.get("event_time")
        trend.append({
            "time": event_time.isoformat() if hasattr(event_time, "isoformat") else event_time,
            "hr": vitals.get("hr"),
            "temp": vitals.get("temp"),
            "spo2": vitals.get("spo2"),
            "bp": vitals.get("bp"),  # often a string like "120/80"
        })
    return trend
