"""Vessel list, creation, and membership — the boat-sharing surface.

Sharing is a membership write, not a data migration: a vessel's documents live
in a sub-collection under it, so granting someone access to the boat grants
access to everything on it at once, and revoking is equally atomic.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.auth import CurrentUser, current_user, resolve_vessel_access
from backend.config import settings
from backend.logger import logger
from backend.schemas.pydantic_models import VesselCreate, VesselRead
from backend.store import VesselStore, get_store
from backend.store.base import ROLES, ROLE_EDITOR, StoreError

router = APIRouter()


class MemberRead(BaseModel):
    uid: str
    role: str
    email: Optional[str] = None
    is_you: bool = False


class MemberInvite(BaseModel):
    email: str
    role: str = ROLE_EDITOR


@router.get("", response_model=List[VesselRead])
def list_my_vessels(
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    vessels = store.list_vessels_for_user(None if user.is_local else user.uid)
    return [v.as_dict() for v in vessels]


@router.post("", response_model=VesselRead, status_code=201)
def create_vessel(
    payload: VesselCreate,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    vessel = store.create_vessel(
        name=payload.name,
        imo_number=payload.imo_number,
        owner_uid=None if user.is_local else user.uid,
    )
    return vessel.as_dict()


@router.get("/{vessel_id}/members", response_model=List[MemberRead])
def list_members(
    vessel_id: str,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    access = resolve_vessel_access(vessel_id, store, user)
    if access.user.is_local:
        return [MemberRead(uid=access.user.uid, role=access.role, is_you=True)]

    return [
        MemberRead(
            uid=uid,
            role=role,
            email=_email_for(uid),
            is_you=uid == user.uid,
        )
        for uid, role in access.vessel.members.items()
    ]


@router.post("/{vessel_id}/members", response_model=List[MemberRead], status_code=201)
def invite_member(
    vessel_id: str,
    payload: MemberInvite,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    """Share this boat with another user, identified by the email they sign in with."""
    access = resolve_vessel_access(vessel_id, store, user)
    access.require_owner()

    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")
    if not settings.require_auth:
        raise HTTPException(
            status_code=400,
            detail="Sharing needs the hosted app — the desktop database is local to this machine.",
        )

    uid = _uid_for_email(payload.email)
    if not uid:
        raise HTTPException(
            status_code=404,
            detail=f"No account for {payload.email}. They need to sign in once first.",
        )

    store.add_member(vessel_id, uid, payload.role)
    return list_members(vessel_id, store, user)


@router.delete("/{vessel_id}/members/{uid}", response_model=List[MemberRead])
def remove_member(
    vessel_id: str,
    uid: str,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    access = resolve_vessel_access(vessel_id, store, user)
    access.require_owner()
    try:
        store.remove_member(vessel_id, uid)
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return list_members(vessel_id, store, user)


# ── Firebase Auth lookups ────────────────────────────────────────────────────
# Best-effort: a missing display email should degrade the members list, never
# fail the request.

def _firebase_auth():
    import firebase_admin
    from firebase_admin import auth as firebase_auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id}
            if settings.firebase_project_id
            else None
        )
    return firebase_auth


def _uid_for_email(email: str) -> Optional[str]:
    try:
        return _firebase_auth().get_user_by_email(email).uid
    except Exception as exc:
        logger.info(f"No Firebase account for {email}: {exc}")
        return None


def _email_for(uid: str) -> Optional[str]:
    try:
        return _firebase_auth().get_user(uid).email
    except Exception:
        return None
