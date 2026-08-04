import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import List, Optional

from backend.auth import VesselAccess, active_vessel
from backend.schemas.pydantic_models import MaintenanceLogRead
from backend.store import VesselStore, get_store

UPLOAD_DIR = Path("backend/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

COLLECTION = "maintenance_logs"


@router.get("/logs", response_model=List[MaintenanceLogRead])
def list_logs(
    resolved: Optional[bool] = None,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    where = [] if resolved is None else [("resolved", resolved)]
    return store.list_docs(access.vessel_id, COLLECTION, where=where)


@router.get("/logs/{log_id}", response_model=MaintenanceLogRead)
def get_log(
    log_id: str,
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    log = store.get_doc(access.vessel_id, COLLECTION, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")
    return log


@router.post("/logs", response_model=MaintenanceLogRead, status_code=201)
async def create_log(
    vessel_id: str = Form(...),
    component_id: str = Form(...),
    logged_by: str = Form(...),
    issue_description: str = Form(...),
    severity: str = Form(...),
    follow_up: Optional[str] = Form(None),
    photos: List[UploadFile] = File(default=[]),
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    access.require_write()

    photo_paths = []
    for photo in photos:
        if photo.filename:
            dest = UPLOAD_DIR / f"{datetime.utcnow().timestamp()}_{photo.filename}"
            with dest.open("wb") as f:
                shutil.copyfileobj(photo.file, f)
            photo_paths.append(str(dest))

    # `vessel_id` is still accepted as a form field for backwards compatibility
    # with existing clients, but the authenticated vessel is what gets written.
    return store.create_doc(
        access.vessel_id,
        COLLECTION,
        {
            "component_id": component_id,
            "logged_by": logged_by,
            "event_time": datetime.utcnow(),
            "issue_description": issue_description,
            "severity": severity,
            "follow_up": follow_up,
            "photo_paths": photo_paths,
            "resolved": False,
        },
    )
