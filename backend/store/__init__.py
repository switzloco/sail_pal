"""Storage abstraction: SQLite on the boat, Firestore in the cloud.

The desktop companion keeps SQLite — it has to work with no connectivity, which
is the whole point of the product. The hosted deployment runs on Cloud Run with
`--min-instances=0` and a container-local `/tmp`, so SQLite there is erased on
every cold start. Anything a user records from a phone needs Firestore.

Both backends implement `VesselStore` (see `base.py`) and both return plain
dicts, which the `*Read` pydantic schemas already accept — their `mode="before"`
validators pass native lists/dicts through untouched and JSON-decode strings, so
one set of schemas serves both.
"""
from backend.store.base import (
    COLLECTIONS,
    CollectionSpec,
    PermissionDenied,
    VesselStore,
)
from backend.store.provider import get_store, reset_store_cache

__all__ = [
    "COLLECTIONS",
    "CollectionSpec",
    "PermissionDenied",
    "VesselStore",
    "get_store",
    "reset_store_cache",
]
