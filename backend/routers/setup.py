import asyncio
import json
import shutil
from typing import AsyncIterator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings

router = APIRouter()


class SetupStatus(BaseModel):
    ollama_installed: bool
    ollama_running: bool
    model_ready: bool
    model_name: str
    install_url: str = "https://ollama.com/download"
    mode: str = "local"  # "local" | "cloud"


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
    if settings.cloud_mode:
        # Bypass all Ollama checks — app is ready immediately.
        return SetupStatus(
            ollama_installed=True,
            ollama_running=True,
            model_ready=True,
            model_name=settings.cloud_model,
            mode="cloud",
        )

    installed = shutil.which("ollama") is not None
    running = await _check_ollama_running() if installed else False
    model_ready = await _check_model_ready(settings.model_primary) if running else False

    return SetupStatus(
        ollama_installed=installed,
        ollama_running=running,
        model_ready=model_ready,
        model_name=settings.model_primary,
        mode="local",
    )


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
