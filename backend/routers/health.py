import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import HealthEvent
from backend.schemas.pydantic_models import HealthEventRead, HealthEventCreate

router = APIRouter()


@router.get("/events", response_model=List[HealthEventRead])
def list_health_events(db: Session = Depends(get_db)):
    return db.query(HealthEvent).order_by(HealthEvent.event_time.desc()).all()


@router.get("/events/{event_id}", response_model=HealthEventRead)
def get_health_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(HealthEvent).filter(HealthEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Health event not found")
    return event


@router.post("/events", response_model=HealthEventRead, status_code=201)
def create_health_event(payload: HealthEventCreate, db: Session = Depends(get_db)):
    vitals_json = None
    if payload.vital_signs:
        vitals_json = payload.vital_signs.model_dump_json()

    event = HealthEvent(
        vessel_id=payload.vessel_id,
        crew_id=payload.crew_id,
        logged_by=payload.logged_by,
        event_time=payload.event_time or datetime.utcnow(),
        symptoms=json.dumps(payload.symptoms or []),
        vital_signs=vitals_json,
        diagnosis=payload.diagnosis,
        treatment=payload.treatment,
        protocol_used=payload.protocol_used,
        severity=payload.severity,
        follow_up_required=payload.follow_up_required,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/crew/{crew_id}/history", response_model=List[HealthEventRead])
def get_crew_health_history(crew_id: str, db: Session = Depends(get_db)):
    return (
        db.query(HealthEvent)
        .filter(HealthEvent.crew_id == crew_id)
        .order_by(HealthEvent.event_time.desc())
        .all()
    )
