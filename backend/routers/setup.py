import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.ai import mode_state
from backend.auth import (
    CurrentUser, VesselAccess, active_vessel, current_user, ensure_vessel_for_user,
)
from backend.config import settings
from backend.db.database import get_db
from backend.schemas.pydantic_models import VesselRead, VesselUpdate
from backend.store import COLLECTIONS, VesselStore, get_store
from backend.store.base import ROLE_OWNER, can_write

router = APIRouter()


class SetupStatus(BaseModel):
    model_config = {"protected_namespaces": ()}

    ollama_installed: bool
    ollama_running: bool
    model_ready: bool
    model_name: str
    # Medical fine-tune — optional bonus; None means MODEL_MEDICAL not configured
    medical_model_ready: Optional[bool] = None
    medical_model_name: Optional[str] = None
    install_url: str = "https://ollama.com/download"
    mode: str = "local"  # "local" | "cloud"
    data_dir: str = ""
    server_is_local: bool = True  # False when backend runs in cloud (can't reach user's Ollama)



class ModeResponse(BaseModel):
    mode: str  # "cloud" | "local"


class ModeRequest(BaseModel):
    mode: str  # "cloud" | "local"


def _is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


async def _check_ollama_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _check_model_ready(model_name: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            if r.status_code != 200:
                return False
            tags = r.json().get("models", [])
            
            # Match exact name, or match prefix/suffix for robustness
            target_base = model_name.split(":")[0]
            target_tag = model_name.split(":")[1] if ":" in model_name else "latest"
            
            for t in tags:
                name = t.get("name", "")
                if name == model_name:
                    return True
                
                # Check for digest-style names or alternate tags
                t_base = name.split(":")[0]
                t_tag = name.split(":")[1] if ":" in name else "latest"
                
                if t_base == target_base and t_tag == target_tag:
                    return True
            return False
    except Exception:
        return False


@router.get("/status", response_model=SetupStatus)
async def setup_status():
    current_mode = mode_state.get_mode()
    if current_mode == "cloud":
        # Bypass all Ollama checks — app is ready immediately.
        return SetupStatus(
            ollama_installed=True,
            ollama_running=True,
            model_ready=True,
            model_name=settings.cloud_model,
            mode="cloud",
            data_dir=settings.data_dir,
            server_is_local=not settings.cloud_mode,
        )

    installed = _is_ollama_installed()
    running = await _check_ollama_running() if installed else False
    model_ready = await _check_model_ready(settings.model_primary) if running else False

    # Check medical fine-tune only when MODEL_MEDICAL is explicitly configured
    med_name = settings.model_medical or None
    med_ready = await _check_model_ready(med_name) if (running and med_name) else None

    return SetupStatus(
        ollama_installed=installed,
        ollama_running=running,
        model_ready=model_ready,
        model_name=settings.model_primary,
        medical_model_ready=med_ready,
        medical_model_name=med_name,
        mode=current_mode,
        data_dir=settings.data_dir,
        server_is_local=not settings.cloud_mode,  # False on Cloud Run (CLOUD_MODE=true)
    )



@router.get("/who-manual")
async def get_who_manual():
    """Serve the bundled WHO International Medical Guide for Ships (3rd ed.) PDF.

    Public-domain document; we bundle it for offline browsing alongside the
    chunked JSON used by the RAG engine.
    """
    # Frozen: PyInstaller extracts to _MEIPASS/backend/data/manuals/
    # Dev: backend/data/manuals/
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        pdf = Path(sys._MEIPASS) / "backend" / "data" / "manuals" / "WHO_IMGS_3rd_Edition.pdf"
    else:
        pdf = Path(__file__).resolve().parent.parent / "data" / "manuals" / "WHO_IMGS_3rd_Edition.pdf"

    if not pdf.exists():
        raise HTTPException(status_code=404, detail="WHO manual not bundled with this build")
    return FileResponse(
        path=str(pdf),
        media_type="application/pdf",
        filename="WHO_IMGS_3rd_Edition.pdf",
    )


@router.get("/mode", response_model=ModeResponse)
async def get_mode():
    return ModeResponse(mode=mode_state.get_mode())


@router.post("/mode", response_model=ModeResponse)
async def set_mode(payload: ModeRequest):
    if payload.mode == "local" and settings.cloud_mode:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot switch to local: this is the hosted web version. "
                "Local Ollama mode requires installing Vessel Ops AI on your own machine. "
                "Visit /welcome/setup for instructions."
            ),
        )
    if payload.mode == "local":
        installed = _is_ollama_installed()
        running = await _check_ollama_running() if installed else False
        model_ready = await _check_model_ready(settings.model_primary) if running else False

        if not installed:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot switch to local: Ollama is not installed on this server. "
                    f"Install it from https://ollama.com/download, then try again."
                ),
            )
        if not running:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot switch to local: Ollama is installed but not reachable at "
                    f"{settings.ollama_host}. Start the Ollama app (or `ollama serve`) and try again."
                ),
            )
        if not model_ready:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot switch to local: Ollama is running but the '{settings.model_primary}' "
                    f"model is not pulled. Run `ollama pull {settings.model_primary}` and try again."
                ),
            )
    elif payload.mode == "cloud":
        from backend.logger import logger
        logger.info(f"Attempting to switch to cloud mode. google_api_key length: {len(settings.google_api_key)}")
        if not settings.google_api_key:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot switch to cloud: GOOGLE_API_KEY is not configured on this server. "
                    "Set the GOOGLE_API_KEY environment variable (or mount the secret) and restart."
                ),
            )
    try:
        mode_state.set_mode(payload.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ModeResponse(mode=mode_state.get_mode())


async def _pull_stream(model_name: str) -> AsyncIterator[str]:
    """Run `ollama pull <model>` and stream JSON progress as SSE."""
    proc = await asyncio.create_subprocess_exec(
        "ollama", "pull", model_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    assert proc.stdout is not None

    async for raw in proc.stdout:
        line = raw.decode().strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = {"status": line}

        yield f"data: {json.dumps(obj)}\n\n"

    await proc.wait()

    if proc.returncode == 0:
        yield f"data: {json.dumps({'status': 'success', 'done': True})}\n\n"
    else:
        yield f"data: {json.dumps({'status': 'error', 'done': True})}\n\n"


@router.post("/pull-model")
async def pull_model():
    """
    Stream `ollama pull` progress as SSE.

    Events carry the raw Ollama JSON progress objects:
      { status, digest?, total?, completed? }
    Final event: { status: "success"|"error", done: true }
    """
    return StreamingResponse(
        _pull_stream(settings.model_primary),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/reset-demo-data")
async def reset_demo_data(
    access: VesselAccess = Depends(active_vessel),
    store: VesselStore = Depends(get_store),
):
    """Wipe this vessel's records to start fresh.

    Scoped to the caller's vessel — on the hosted deployment this must never
    reach across into another user's boat.
    """
    access.require_write()
    cleared = 0
    for collection in ("maintenance_logs", "health_events", "components", "crew"):
        for doc in store.list_docs(access.vessel_id, collection):
            spec_id = COLLECTIONS[collection].id_field
            if store.delete_doc(access.vessel_id, collection, doc[spec_id]):
                cleared += 1
    # The vessel record itself survives so the user keeps their boat's identity.
    return {"status": "success", "message": "Demo data cleared.", "records_cleared": cleared}


@router.get("/vessel-info", response_model=VesselRead)
async def get_vessel_info(
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    return ensure_vessel_for_user(store, user).as_dict()


@router.post("/vessel-info", response_model=VesselRead)
async def update_vessel_info(
    payload: VesselUpdate,
    store: VesselStore = Depends(get_store),
    user: CurrentUser = Depends(current_user),
):
    vessel = ensure_vessel_for_user(store, user)
    role = ROLE_OWNER if user.is_local else vessel.role_for(user.uid)
    if not can_write(role):
        raise HTTPException(status_code=403, detail="You have read-only access to this vessel.")

    patch = {}
    if payload.name:
        patch["name"] = payload.name
    if payload.imo_number is not None:
        patch["imo_number"] = payload.imo_number
    if patch:
        vessel = store.update_vessel(vessel.vessel_id, patch)
    return vessel.as_dict()
