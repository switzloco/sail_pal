from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import SyncQueue
from backend.schemas.pydantic_models import SyncStatusRead
from backend.logger import logger

router = APIRouter()

# Phase 2: Firebase sync will be wired here.
# The sync_queue table already tracks every insert/update/delete
# that needs to be pushed to Firestore when internet is available.


@router.get("/status", response_model=SyncStatusRead)
def sync_status(db: Session = Depends(get_db)):
    depth = db.query(SyncQueue).filter(SyncQueue.synced_at == None).count()
    return SyncStatusRead(queue_depth=depth, last_sync=None)


@router.post("/now")
def sync_now(db: Session = Depends(get_db)):
    pending = db.query(SyncQueue).filter(SyncQueue.synced_at == None).all()
    count = 0
    for item in pending:
        logger.info(f"Mock syncing {item.action} on {item.entity_type} to cloud")
        item.synced_at = datetime.utcnow()
        count += 1
    
    if count > 0:
        db.commit()

    return {"status": "success", "synced_items": count}
