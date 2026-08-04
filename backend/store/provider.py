"""Chooses the storage backend and hands it to routers as a dependency."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import get_db
from backend.logger import logger
from backend.store.base import VesselStore
from backend.store.sql_store import SqlStore

_firestore_client: Optional[Any] = None


def firestore_client() -> Any:
    """Lazily initialise the Firestore client.

    Deliberately not created at import time: the desktop build never needs it,
    and on Cloud Run the credentials come from the runtime service account, which
    isn't available until the container is actually serving.
    """
    global _firestore_client
    if _firestore_client is None:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            # Application Default Credentials: the Cloud Run service account.
            firebase_admin.initialize_app(
                options={"projectId": settings.firebase_project_id}
                if settings.firebase_project_id
                else None
            )
        _firestore_client = firestore.client()
    return _firestore_client


def set_firestore_client(client: Optional[Any]) -> None:
    """Inject a client — used by tests to swap in an in-memory double."""
    global _firestore_client
    _firestore_client = client


def reset_store_cache() -> None:
    set_firestore_client(None)


def use_firestore() -> bool:
    """Storage backend follows the deployment, not the runtime AI mode toggle.

    A user switching the hosted app to "local" AI mode is saying something about
    which model answers their questions. It must not silently move their vessel
    records onto a SQLite file that Cloud Run erases on the next cold start.
    """
    return settings.use_firestore


def get_store(db: Session = Depends(get_db)) -> VesselStore:
    if use_firestore():
        from backend.store.firestore_store import FirestoreStore

        try:
            return FirestoreStore(firestore_client())
        except Exception as exc:  # pragma: no cover - depends on GCP runtime
            # Falling back to ephemeral SQLite would silently drop the user's
            # data on the next cold start, so make the failure loud instead.
            logger.error(f"Firestore unavailable, refusing to fall back to SQLite: {exc}")
            raise
    return SqlStore(db)
