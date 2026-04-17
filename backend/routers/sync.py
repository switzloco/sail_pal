from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import SyncQueue
from backend.schemas.pydantic_models import SyncStatusRead

router = APIRouter()

# Phase 2: Firebase sync will be wired here.
# The sync_queue table already tracks every insert/update/delete
# that needs to be pushed to Firestore when internet is available.


@router.get("/status", response_model=SyncStatusRead)
def sync_status(db: Session = Depends(get_db)):
    depth = db.query(SyncQueue).filter(SyncQueue.synced_at == None).count()
    return SyncStatusRead(queue_depth=depth, last_sync=None)


@router.post("/now", status_code=501)
def sync_now():
    return {"detail": "Firebase sync not enabled yet — coming in Phase 2"}
