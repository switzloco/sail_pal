"""Firebase Auth for the hosted deployment.

Two very different threat models, one codebase:

* **Desktop / local mode** — the SQLite database sits on one person's laptop.
  Anyone who can reach the API can already open the file. Requiring a login
  would add friction at sea and protect nothing, so auth is off
  (`require_auth=False`) and the caller is treated as the vessel owner.

* **Hosted mode** — the app is on the public internet and holds real crew
  medical records. Every data route needs a verified Firebase ID token, and
  every vessel access is checked against that vessel's membership map.

Authorization is enforced here rather than in Firestore security rules because
the backend uses the Admin SDK, which bypasses rules entirely. The rules file
(`firestore.rules`) therefore denies all direct client access — the API is the
only way in, and this module is its front door.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

from backend.config import settings
from backend.logger import logger
from backend.store.base import (
    ROLE_OWNER,
    Vessel,
    VesselStore,
    can_administer,
    can_write,
)
from backend.store.provider import get_store

# Stand-in identity for local/desktop mode, where there are no accounts.
LOCAL_UID = "local-owner"


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: Optional[str] = None
    #: True when auth is disabled (desktop mode), not a real verified identity.
    is_local: bool = False


def _verify_id_token(token: str) -> dict:
    import firebase_admin
    from firebase_admin import auth as firebase_auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id}
            if settings.firebase_project_id
            else None
        )
    return firebase_auth.verify_id_token(token)


async def current_user(request: Request) -> CurrentUser:
    """Resolve the caller. Raises 401 in hosted mode without a valid token."""
    if not settings.require_auth:
        return CurrentUser(uid=LOCAL_UID, is_local=True)

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Sign in to access vessel records.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = header[len("Bearer ") :].strip()
    try:
        claims = _verify_id_token(token)
    except Exception as exc:
        logger.warning(f"Rejected ID token: {exc}")
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")

    uid = claims.get("uid") or claims.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Token carried no user id.")
    return CurrentUser(uid=uid, email=claims.get("email"))


async def optional_user(request: Request) -> Optional[CurrentUser]:
    """Like `current_user`, but returns None instead of 401.

    For routes that must answer before sign-in — the setup status probe and the
    AI-mode banner, which the sign-in screen itself renders.
    """
    try:
        return await current_user(request)
    except HTTPException:
        return None


# ── Vessel-scoped authorization ──────────────────────────────────────────────


def _role_for(vessel: Vessel, user: CurrentUser) -> Optional[str]:
    # Desktop mode has no accounts, so the local caller owns whatever is there.
    return ROLE_OWNER if user.is_local else vessel.role_for(user.uid)


class VesselAccess:
    """Resolved vessel + the caller's role on it."""

    def __init__(self, vessel: Vessel, user: CurrentUser, role: str):
        self.vessel = vessel
        self.user = user
        self.role = role

    @property
    def vessel_id(self) -> str:
        return self.vessel.vessel_id

    def require_write(self) -> None:
        if not can_write(self.role):
            raise HTTPException(
                status_code=403,
                detail="You have read-only access to this vessel.",
            )

    def require_owner(self) -> None:
        if not can_administer(self.role):
            raise HTTPException(
                status_code=403,
                detail="Only the vessel owner can change who has access.",
            )


def resolve_vessel_access(
    vessel_id: str,
    store: VesselStore,
    user: CurrentUser,
) -> VesselAccess:
    vessel = store.get_vessel(vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    role = _role_for(vessel, user)
    if role is None:
        # Deliberately 404, not 403: a stranger probing vessel ids should not be
        # able to tell an existing boat from a non-existent one.
        raise HTTPException(status_code=404, detail="Vessel not found")
    return VesselAccess(vessel, user, role)


def ensure_vessel_for_user(store: VesselStore, user: CurrentUser) -> Vessel:
    """The caller's vessel, created empty on first use if they have none.

    Signing in on a phone and hitting a 404 on every screen would be a terrible
    first run, so the first request mints an unnamed boat the user can rename.
    """
    vessels = store.list_vessels_for_user(None if user.is_local else user.uid)
    if vessels:
        return vessels[0]
    return store.create_vessel(
        name="My Vessel",
        imo_number=None,
        owner_uid=None if user.is_local else user.uid,
    )


async def active_vessel(
    request: Request,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
) -> VesselAccess:
    """The vessel this request is about.

    Explicit `X-Vessel-Id` header wins, so a user with more than one boat can
    switch without every route growing a path parameter. Otherwise falls back to
    their first vessel — the common case, and the whole case on desktop.
    """
    requested = request.headers.get("X-Vessel-Id") or request.query_params.get("vessel_id")
    if requested:
        return resolve_vessel_access(requested, store, user)

    vessel = ensure_vessel_for_user(store, user)
    role = _role_for(vessel, user) or ROLE_OWNER
    return VesselAccess(vessel, user, role)
