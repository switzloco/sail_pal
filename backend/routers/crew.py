from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.auth import VesselAccess, active_vessel
from backend.schemas.pydantic_models import CrewMemberRead, CrewMemberCreate, CrewMemberUpdate
from backend.store import VesselStore, get_store

router = APIRouter()

COLLECTION = "crew"


@router.get("", response_model=List[CrewMemberRead])
def list_crew(
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    return store.list_docs(access.vessel_id, COLLECTION, where=[("is_active", True)])


@router.get("/{crew_id}", response_model=CrewMemberRead)
def get_crew_member(
    crew_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    member = store.get_doc(access.vessel_id, COLLECTION, crew_id)
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return member


@router.post("", response_model=CrewMemberRead, status_code=201)
def create_crew_member(
    payload: CrewMemberCreate,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    data = payload.model_dump(exclude_unset=True)
    # The vessel comes from the authenticated request, never the body — a
    # client must not be able to write into someone else's boat by id.
    data.pop("vessel_id", None)
    data.setdefault("allergies", [])
    data.setdefault("emergency_contact", {})
    data["is_active"] = True
    return store.create_doc(access.vessel_id, COLLECTION, data)


@router.patch("/{crew_id}", response_model=CrewMemberRead)
def update_crew_member(
    crew_id: str,
    payload: CrewMemberUpdate,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    updated = store.update_doc(
        access.vessel_id, COLLECTION, crew_id, payload.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return updated


@router.delete("/{crew_id}", status_code=204)
def delete_crew_member(
    crew_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    if not store.delete_doc(access.vessel_id, COLLECTION, crew_id):
        raise HTTPException(status_code=404, detail="Crew member not found")
    return None
