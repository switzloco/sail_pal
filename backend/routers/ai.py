import asyncio
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncIterator, Optional

from backend.config import settings
from backend.db.database import get_db
from backend.schemas.pydantic_models import MedicalQueryRequest, ComponentAnalysisRequest
from backend.ai.prompt_templates import (
    MEDICAL_SYSTEM, ENGINE_SYSTEM, DISCLAIMER,
    MOCK_MEDICAL_CHUNKS, MOCK_ENGINE_CHUNKS,
)

router = APIRouter()


async def _tokens_to_sse(token_iter: AsyncIterator[str]):
    async for token in token_iter:
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def _mock_stream(chunks: list[str], delay: float = 0.15) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk
        await asyncio.sleep(delay)


async def _llm_tokens(
    system: str,
    user_prompt: str,
    images: Optional[list[bytes]] = None,
) -> AsyncIterator[str]:
    """Route to cloud or mock depending on settings."""
    if settings.cloud_mode:
        from backend.ai.google_client import GoogleSimulationClient
        client = GoogleSimulationClient(
            api_key=settings.google_api_key,
            model=settings.cloud_model,
        )
        async for token in client.chat_stream(system, user_prompt, images=images):
            yield token
    else:
        # Phase 2 will wire Ollama here; use mock for now
        chunks = (
            MOCK_MEDICAL_CHUNKS if "medical" in system.lower() else MOCK_ENGINE_CHUNKS
        )
        async for token in _mock_stream(chunks):
            yield token


@router.post("/medical-query")
async def medical_query(payload: MedicalQueryRequest, db: Session = Depends(get_db)):
    """Stream an AI medical guidance response (cloud or mock)."""
    from backend.db.models import CrewMember
    crew = db.query(CrewMember).filter(CrewMember.crew_id == payload.crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    user_prompt = (
        f"Patient: {crew.full_name}, {crew.role}\n"
        f"Severity: {payload.severity.upper()}\n"
        f"Symptoms: {', '.join(payload.symptoms)}\n"
        + (f"Vitals: {payload.vitals}\n" if payload.vitals else "")
        + f"\nPlease assess and provide immediate treatment guidance. "
        f"End with: {DISCLAIMER}"
    )

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(MEDICAL_SYSTEM, user_prompt)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/analyze-component")
async def analyze_component(
    component_id: str = Form(...),
    issue_description: str = Form(...),
    severity: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Stream an AI component fault analysis (cloud with vision, or mock)."""
    from backend.db.models import Component
    component = db.query(Component).filter(Component.component_id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    image_bytes: Optional[list[bytes]] = None
    if image and settings.cloud_mode:
        image_bytes = [await image.read()]

    user_prompt = (
        f"Component: {component.name} ({component.system})\n"
        f"Issue: {issue_description}\n"
        f"Severity: {severity.upper()}\n"
        + ("An image of the component has been attached.\n" if image_bytes else "")
        + f"\nDiagnose the fault and provide repair/safety guidance. "
        f"End with: {DISCLAIMER}"
    )

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(ENGINE_SYSTEM, user_prompt, images=image_bytes)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
