from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from backend.auth import VesselAccess, active_vessel
from backend.schemas.pydantic_models import ComponentRead, ComponentCreate, ComponentUpdate
from backend.store import VesselStore, get_store

router = APIRouter()

COLLECTION = "components"


@router.get("", response_model=List[ComponentRead])
def list_components(
    system: Optional[str] = None,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    where = [("is_active", True)]
    if system:
        where.append(("system", system))
    return store.list_docs(access.vessel_id, COLLECTION, where=where)


@router.get("/{component_id}", response_model=ComponentRead)
def get_component(
    component_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    component = store.get_doc(access.vessel_id, COLLECTION, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@router.post("", response_model=ComponentRead, status_code=201)
def create_component(
    payload: ComponentCreate,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    data = payload.model_dump(exclude_unset=True)
    data.pop("vessel_id", None)
    data.setdefault("spare_parts", [])
    data["is_active"] = True
    return store.create_doc(access.vessel_id, COLLECTION, data)


@router.patch("/{component_id}", response_model=ComponentRead)
def update_component(
    component_id: str,
    payload: ComponentUpdate,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    updated = store.update_doc(
        access.vessel_id, COLLECTION, component_id, payload.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Component not found")
    return updated


@router.delete("/{component_id}", status_code=204)
def delete_component(
    component_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()
    if not store.delete_doc(access.vessel_id, COLLECTION, component_id):
        raise HTTPException(status_code=404, detail="Component not found")
    return None
