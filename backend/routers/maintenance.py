import json
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.db.database import get_db
from backend.db.models import MaintenanceLog
from backend.schemas.pydantic_models import MaintenanceLogRead

UPLOAD_DIR = Path("backend/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


@router.get("/logs", response_model=List[MaintenanceLogRead])
def list_logs(resolved: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(MaintenanceLog)
    if resolved is not None:
        q = q.filter(MaintenanceLog.resolved == resolved)
    return q.order_by(MaintenanceLog.event_time.desc()).all()


@router.get("/logs/{log_id}", response_model=MaintenanceLogRead)
def get_log(log_id: str, db: Session = Depends(get_db)):
    log = db.query(MaintenanceLog).filter(MaintenanceLog.log_id == log_id).first()
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
    db: Session = Depends(get_db),
):
    photo_paths = []
    for photo in photos:
        if photo.filename:
            dest = UPLOAD_DIR / f"{datetime.utcnow().timestamp()}_{photo.filename}"
            with dest.open("wb") as f:
                shutil.copyfileobj(photo.file, f)
            photo_paths.append(str(dest))

    log = MaintenanceLog(
        vessel_id=vessel_id,
        component_id=component_id,
        logged_by=logged_by,
        event_time=datetime.utcnow(),
        issue_description=issue_description,
        severity=severity,
        follow_up=follow_up,
        photo_paths=json.dumps(photo_paths),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
