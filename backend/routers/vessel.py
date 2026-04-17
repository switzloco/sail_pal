import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import Component
from backend.schemas.pydantic_models import ComponentRead, ComponentCreate, ComponentUpdate

router = APIRouter()


@router.get("", response_model=List[ComponentRead])
def list_components(system: str = None, db: Session = Depends(get_db)):
    q = db.query(Component).filter(Component.is_active == True)
    if system:
        q = q.filter(Component.system == system)
    return q.order_by(Component.system, Component.name).all()


@router.get("/{component_id}", response_model=ComponentRead)
def get_component(component_id: str, db: Session = Depends(get_db)):
    component = db.query(Component).filter(Component.component_id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@router.post("", response_model=ComponentRead, status_code=201)
def create_component(payload: ComponentCreate, db: Session = Depends(get_db)):
    component = Component(
        vessel_id=payload.vessel_id,
        name=payload.name,
        system=payload.system,
        manufacturer=payload.manufacturer,
        model_number=payload.model_number,
        serial_number=payload.serial_number,
        install_date=payload.install_date,
        location=payload.location,
        manual_ref=payload.manual_ref,
        spare_parts=json.dumps(payload.spare_parts or []),
        notes=payload.notes,
    )
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


@router.patch("/{component_id}", response_model=ComponentRead)
def update_component(component_id: str, payload: ComponentUpdate, db: Session = Depends(get_db)):
    component = db.query(Component).filter(Component.component_id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, field, value)
    db.commit()
    db.refresh(component)
    return component
