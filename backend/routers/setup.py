import asyncio
import json
import shutil
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.ai import mode_state
from backend.config import settings
from backend.db.database import get_db
from backend.db.models import Vessel, CrewMember, HealthEvent, Component, MaintenanceLog
from backend.schemas.pydantic_models import VesselRead, VesselUpdate

router = APIRouter()


class SetupStatus(BaseModel):
    ollama_installed: bool
    ollama_running: bool
    model_ready: bool
    model_name: str
    install_url: str = "https://ollama.com/download"
    mode: str = "local"  # "local" | "cloud"
    data_dir: str = ""



class ModeResponse(BaseModel):
    mode: str  # "cloud" | "local"


class ModeRequest(BaseModel):
    mode: str  # "cloud" | "local"


async def _check_ollama_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _check_model_ready(model_name: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            if r.status_code != 200:
                return False
            tags = r.json().get("models", [])
            # Ollama model names may include digest suffix — match on prefix
            return any(
                t.get("name", "").split(":")[0] == model_name.split(":")[0]
                and (
                    ":" not in model_name
                    or t.get("name", "").endswith(model_name.split(":")[1])
                )
                for t in tags
            )
    except Exception:
        return False


@router.get("/status", response_model=SetupStatus)
async def setup_status():
    current_mode = mode_state.get_mode()

    installed = shutil.which("ollama") is not None
    running = await _check_ollama_running() if installed else False
    model_ready = await _check_model_ready(settings.model_primary) if running else False

    return SetupStatus(
        ollama_installed=installed,
        ollama_running=running,
        model_ready=model_ready,
        model_name=settings.model_primary,
        mode=current_mode,
        data_dir=settings.data_dir,
    )



@router.get("/mode", response_model=ModeResponse)
async def get_mode():
    return ModeResponse(mode=mode_state.get_mode())


@router.post("/mode", response_model=ModeResponse)
async def set_mode(payload: ModeRequest):
    if payload.mode == "local":
        running = await _check_ollama_running()
        model_ready = await _check_model_ready(settings.model_primary) if running else False
        if not model_ready:
            raise HTTPException(
                status_code=409,
                detail="Cannot switch to local: Ollama is not running or the model is not pulled yet.",
            )
    elif payload.mode == "cloud":
        from backend.logger import logger
        logger.info(f"Attempting to switch to cloud mode. google_api_key length: {len(settings.google_api_key)}")
        if not settings.google_api_key:
            raise HTTPException(
                status_code=409,
                detail="Cannot switch to cloud: GOOGLE_API_KEY is not configured on this server.",
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
async def reset_demo_data(db: Session = Depends(get_db)):
    """Wipe all user-generated data to start fresh."""
    try:
        db.query(MaintenanceLog).delete()
        db.query(HealthEvent).delete()
        db.query(Component).delete()
        db.query(CrewMember).delete()
        # We keep the Vessel record but reset its name if needed? 
        # Or just leave it for the user to rename.
        db.commit()
        return {"status": "success", "message": "Demo data cleared."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vessel-info", response_model=VesselRead)
async def get_vessel_info(db: Session = Depends(get_db)):
    vessel = db.query(Vessel).first()
    if not vessel:
        # Create a default one if missing
        vessel = Vessel(name="My Vessel", imo_number="0000000")
        db.add(vessel)
        db.commit()
        db.refresh(vessel)
    return vessel


@router.post("/vessel-info", response_model=VesselRead)
async def update_vessel_info(payload: VesselUpdate, db: Session = Depends(get_db)):
    vessel = db.query(Vessel).first()
    if not vessel:
        vessel = Vessel(name="My Vessel", imo_number="0000000")
        db.add(vessel)
        db.commit()
        db.refresh(vessel)
    
    if payload.name:
        vessel.name = payload.name
    if payload.imo_number is not None:
        vessel.imo_number = payload.imo_number
        
    db.commit()
    db.refresh(vessel)
    return vessel
