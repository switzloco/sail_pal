import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.db.database import get_db
from backend.db.models import HealthEvent, MaintenanceLog
from backend.schemas.pydantic_models import MedicalQueryRequest, ComponentAnalysisRequest
from backend.ai.prompt_templates import MOCK_MEDICAL_CHUNKS, MOCK_ENGINE_CHUNKS

router = APIRouter()


async def _sse_stream(chunks: list[str], delay: float = 0.15):
    """Yield SSE-formatted chunks with a small delay to simulate streaming."""
    for chunk in chunks:
        yield f"data: {json.dumps({'token': chunk})}\n\n"
        await asyncio.sleep(delay)
    yield f"data: {json.dumps({'done': True})}\n\n"


@router.post("/medical-query")
async def medical_query(payload: MedicalQueryRequest, db: Session = Depends(get_db)):
    """
    Stream an AI medical guidance response.

    Phase 1: returns mock SSE stream with realistic placeholder guidance.
    Phase 2: routes to Ollama (gemma4:12b / gemma4:27b based on severity),
             prepends RAG context from medical_protocols collection.
    """
    # Validate crew exists
    from backend.db.models import CrewMember
    crew = db.query(CrewMember).filter(CrewMember.crew_id == payload.crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    intro = (
        f"Medical assessment for {crew.full_name} ({crew.role}) — "
        f"severity: {payload.severity.upper()}\n"
        f"Reported symptoms: {', '.join(payload.symptoms)}\n\n"
    )
    chunks = [intro] + MOCK_MEDICAL_CHUNKS

    return StreamingResponse(_sse_stream(chunks), media_type="text/event-stream")


@router.post("/analyze-component")
async def analyze_component(
    component_id: str = Form(...),
    issue_description: str = Form(...),
    severity: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Stream an AI component fault analysis and maintenance guidance response.

    Phase 1: returns mock SSE stream.
    Phase 2: runs two-pass multimodal analysis (image → fault JSON → guidance)
             with RAG context from engine_manuals collection.
    """
    from backend.db.models import Component
    component = db.query(Component).filter(Component.component_id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    intro = (
        f"Component fault analysis: {component.name} ({component.system})\n"
        f"Reported issue: {issue_description} — severity: {severity.upper()}\n\n"
    )
    chunks = [intro] + MOCK_ENGINE_CHUNKS

    return StreamingResponse(_sse_stream(chunks), media_type="text/event-stream")
