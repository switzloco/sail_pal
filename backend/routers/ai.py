import asyncio
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import AsyncIterator, List, Optional

from backend.ai import mode_state
from backend.config import settings
from backend.db.database import get_db
from backend.schemas.pydantic_models import MedicalQueryRequest, ComponentAnalysisRequest
from backend.ai.prompt_templates import (
    MEDICAL_SYSTEM, ENGINE_SYSTEM, GENERAL_SYSTEM, DISCLAIMER,
)
from backend.ai.rag_engine import RAGEngine
from backend.ai.image_parser import parse_component_image

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    crew_id: Optional[str] = None
    component_id: Optional[str] = None


async def _tokens_to_sse(token_iter: AsyncIterator[str]):
    async for token in token_iter:
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def _llm_tokens(
    system: str,
    user_prompt: str,
    images: Optional[list[bytes]] = None,
    severity: str = "minor",
) -> AsyncIterator[str]:
    """Route to cloud (Google) or local (Ollama) depending on runtime mode."""
    if mode_state.is_cloud():
        from backend.ai.google_client import GoogleSimulationClient
        client = GoogleSimulationClient(
            api_key=settings.google_api_key,
            model=settings.cloud_model,
        )
        async for token in client.chat_stream(system, user_prompt, images=images):
            yield token
    else:
        from backend.ai.ollama_client import OllamaRouter
        router = OllamaRouter(
            host=settings.ollama_host,
            model_primary=settings.model_primary,
            model_scale=settings.model_scale,
        )
        async for token in router.chat_stream(
            system, user_prompt, severity=severity, images=images
        ):
            yield token


@router.post("/medical-query")
async def medical_query(payload: MedicalQueryRequest, db: Session = Depends(get_db)):
    """Stream an AI medical guidance response (cloud or local)."""
    from backend.db.models import CrewMember
    crew = db.query(CrewMember).filter(CrewMember.crew_id == payload.crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    user_prompt = (
        f"Patient: {crew.full_name}, {crew.role}\n"
        f"Severity: {payload.severity.upper()}\n"
        f"Symptoms: {', '.join(payload.symptoms)}\n"
        + (f"Vitals: {payload.vitals}\n" if payload.vitals else "")
    )

    rag = RAGEngine()
    rag_results = rag.query("medical_protocols", ", ".join(payload.symptoms), k=2)
    if rag_results:
        user_prompt += "\nRelevant Protocol Excerpts:\n"
        for r in rag_results:
            user_prompt += f"- {r['text']} (Source: {r['metadata'].get('source', 'Unknown')})\n"

    user_prompt += (
        f"\nPlease assess and provide immediate treatment guidance. "
        f"End with: {DISCLAIMER}"
    )

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(MEDICAL_SYSTEM, user_prompt, severity=payload.severity)),
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
    """Stream an AI component fault analysis (cloud with vision, or local)."""
    from backend.db.models import Component
    component = db.query(Component).filter(Component.component_id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    image_bytes: Optional[list[bytes]] = None
    image_analysis = None
    if image:
        image_bytes = [await image.read()]
        image_analysis = await parse_component_image(image_bytes[0], component.name)

    user_prompt = (
        f"Component: {component.name} ({component.system})\n"
        f"Issue: {issue_description}\n"
        f"Severity: {severity.upper()}\n"
    )

    if image_analysis:
        user_prompt += (
            f"Image Analysis: {image_analysis.get('fault_type')}\n"
            f"Affected Parts: {', '.join(image_analysis.get('affected_parts', []))}\n"
            f"Confidence: {image_analysis.get('confidence')}\n"
        )
    elif image_bytes:
        user_prompt += "An image of the component has been attached.\n"

    rag = RAGEngine()
    rag_query = f"{component.name} {component.model_number or ''} {issue_description}"
    if image_analysis:
        rag_query += f" {image_analysis.get('fault_type', '')}"

    rag_results = rag.query("engine_manuals", rag_query, k=2)
    if rag_results:
        user_prompt += "\nRelevant Manual Excerpts:\n"
        for r in rag_results:
            user_prompt += f"- {r['text']} (Source: {r['metadata'].get('source', 'Unknown')})\n"

    user_prompt += (
        f"\nDiagnose the fault and provide repair/safety guidance. "
        f"End with: {DISCLAIMER}"
    )

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(ENGINE_SYSTEM, user_prompt, images=image_bytes, severity=severity)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Multi-turn chat with Gemma, optionally grounded in a crew member or component."""
    from backend.db.models import CrewMember, Component

    context_lines: list[str] = []
    system = GENERAL_SYSTEM

    if payload.crew_id:
        crew = db.query(CrewMember).filter(CrewMember.crew_id == payload.crew_id).first()
        if crew:
            context_lines.append(f"Patient under discussion: {crew.full_name} ({crew.role})")
            if crew.blood_type:
                context_lines.append(f"  Blood type: {crew.blood_type}")
            if crew.allergies:
                allergies = crew.allergies if isinstance(crew.allergies, list) else json.loads(crew.allergies or "[]")
                if allergies:
                    context_lines.append(f"  Allergies: {', '.join(allergies)}")
            if crew.medical_notes:
                context_lines.append(f"  Medical notes: {crew.medical_notes}")
            system = MEDICAL_SYSTEM

    if payload.component_id:
        comp = db.query(Component).filter(Component.component_id == payload.component_id).first()
        if comp:
            context_lines.append(f"Component under discussion: {comp.name} ({comp.system})")
            if comp.manufacturer:
                context_lines.append(f"  Manufacturer: {comp.manufacturer} {comp.model_number or ''}")
            if comp.location:
                context_lines.append(f"  Location: {comp.location}")
            if comp.notes:
                context_lines.append(f"  Notes: {comp.notes}")
            system = ENGINE_SYSTEM

    rag_query_text = payload.messages[-1].content
    rag = RAGEngine()
    if payload.crew_id:
        rag_results = rag.query("medical_protocols", rag_query_text, k=2)
        if rag_results:
            context_lines.append("\nRelevant Protocol Excerpts:")
            for r in rag_results:
                context_lines.append(f"- {r['text']} (Source: {r['metadata'].get('source', 'Unknown')})")
    elif payload.component_id:
        rag_results = rag.query("engine_manuals", rag_query_text, k=2)
        if rag_results:
            context_lines.append("\nRelevant Manual Excerpts:")
            for r in rag_results:
                context_lines.append(f"- {r['text']} (Source: {r['metadata'].get('source', 'Unknown')})")

    if context_lines:
        system = system + "\n\nContext for this conversation:\n" + "\n".join(context_lines)

    transcript = "\n\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
        for m in payload.messages
    )
    transcript += "\n\nAssistant:"

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(system, transcript)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/upload-manual")
async def upload_manual(
    category: str = Form(..., description="'medical_protocols' or 'engine_manuals'"),
    file: UploadFile = File(...)
):
    """Upload a PDF manual, extract its text using PyMuPDF, and add it to the local RAG ChromaDB."""
    import fitz  # PyMuPDF
    import uuid
    import tempfile
    import os
    
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    if category not in ("medical_protocols", "engine_manuals"):
        raise HTTPException(status_code=400, detail="Invalid category. Must be 'medical_protocols' or 'engine_manuals'")
        
    try:
        content = await file.read()
        
        # Save to temporary file to read with fitz
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        doc = fitz.open(tmp_path)
        chunks = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if not text.strip():
                continue
                
            chunks.append({
                "text": text.strip(),
                "metadata": {"source": file.filename, "page": page_num + 1}
            })
            
        doc.close()
        os.remove(tmp_path)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No readable text found in PDF")
        
        # Add to ChromaDB
        from backend.ai.rag_engine import RAGEngine
        rag = RAGEngine()
        ids = [f"{file.filename}-{c['metadata']['page']}-{uuid.uuid4().hex[:8]}" for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        # Add in batches to avoid ChromaDB limits
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            rag.add_documents(
                collection_name=category,
                documents=texts[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                ids=ids[i:i+batch_size]
            )
            
        return {"status": "success", "pages_processed": len(chunks), "filename": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.get("/knowledge-stats")
async def get_knowledge_stats():
    engine = RAGEngine()
    stats = {}
    for coll in ["medical_protocols", "engine_manuals"]:
        try:
            collection = engine.client.get_collection(coll)
            stats[coll] = collection.count()
        except Exception:
            stats[coll] = 0
    return stats
