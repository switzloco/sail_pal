import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import CrewMember
from backend.schemas.pydantic_models import CrewMemberRead, CrewMemberCreate, CrewMemberUpdate

router = APIRouter()


@router.get("", response_model=List[CrewMemberRead])
def list_crew(db: Session = Depends(get_db)):
    return db.query(CrewMember).filter(CrewMember.is_active == True).all()


@router.get("/{crew_id}", response_model=CrewMemberRead)
def get_crew_member(crew_id: str, db: Session = Depends(get_db)):
    member = db.query(CrewMember).filter(CrewMember.crew_id == crew_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return member


@router.post("", response_model=CrewMemberRead, status_code=201)
def create_crew_member(payload: CrewMemberCreate, db: Session = Depends(get_db)):
    member = CrewMember(
        vessel_id=payload.vessel_id,
        full_name=payload.full_name,
        role=payload.role,
        date_of_birth=payload.date_of_birth,
        blood_type=payload.blood_type,
        allergies=json.dumps(payload.allergies or []),
        medical_notes=payload.medical_notes,
        emergency_contact=json.dumps(payload.emergency_contact or {}),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{crew_id}", response_model=CrewMemberRead)
def update_crew_member(crew_id: str, payload: CrewMemberUpdate, db: Session = Depends(get_db)):
    member = db.query(CrewMember).filter(CrewMember.crew_id == crew_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("allergies", "emergency_contact") and value is not None:
            value = json.dumps(value)
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member
