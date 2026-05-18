import asyncio
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import AsyncIterator, List, Optional

from backend.ai import mode_state
from backend.config import settings
from backend.db.database import get_db
from backend.schemas.pydantic_models import MedicalQueryRequest, ComponentAnalysisRequest
from backend.ai.prompt_templates import (
    MEDICAL_SYSTEM, ENGINE_SYSTEM, GENERAL_SYSTEM, TRIVIA_SYSTEM, MPIC_STUDY_SYSTEM, DISCLAIMER, SUCCINCT_MODIFIER, CITATION_INSTRUCTIONS
)
from backend.ai.rag_engine import RAGEngine
from backend.ai.image_parser import parse_component_image

_rag_engine = None

def get_rag_engine():
    """Lazy-load RAGEngine to prevent blocking startup with heavy models."""
    global _rag_engine
    if _rag_engine is None:
        from backend.ai.rag_engine import RAGEngine
        _rag_engine = RAGEngine()
    return _rag_engine

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    crew_id: Optional[str] = None
    component_id: Optional[str] = None
    succinct: bool = True


async def _tokens_to_sse(token_iter: AsyncIterator[str], model_label: Optional[str] = None):
    if model_label:
        yield f"data: {json.dumps({'model': model_label})}\n\n"
    async for token in token_iter:
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


# Clinical / medical-intent keywords that should route chat to the medical
# fine-tune even when the WHO IMGS BM25 retriever doesn't match. The IMGS
# uses plain language ("loss of interest") so clinical terms like "anhedonia"
# fall through unless we catch them here.
_MEDICAL_INTENT_KEYWORDS = {
    # Mental health
    "anhedonia", "depression", "depressed", "suicidal", "suicide", "anxiety",
    "psychosis", "psychotic", "panic", "mania", "bipolar", "ptsd",
    # Common symptoms
    "pain", "fever", "vomit", "vomiting", "nausea", "diarrhea", "diarrhoea",
    "bleeding", "wound", "laceration", "fracture", "burn", "rash", "infection",
    "headache", "dizzy", "dizziness", "unconscious", "seizure", "shock",
    "chest pain", "shortness of breath", "swelling", "abscess", "toothache",
    # Body systems / domains
    "asthma", "diabetes", "hypothermia", "hyperthermia", "heatstroke",
    "drowning", "poisoning", "overdose", "allergy", "allergic", "anaphylaxis",
    # Care actions
    "first aid", "cpr", "resuscitate", "triage", "medication", "antibiotic",
    "dosage", "dose", "injection", "suture",
}


def _has_medical_intent(text: str) -> bool:
    """Cheap keyword pass to catch medical queries the BM25 retriever misses."""
    if not text:
        return False
    lowered = text.lower()
    return any(kw in lowered for kw in _MEDICAL_INTENT_KEYWORDS)


def _model_label(model_override: Optional[str]) -> str:
    """Friendly badge text for the chat UI.

    Returns "Vessel Ops Medical" when the medical fine-tune is selected and
    is actually a distinct model from the primary; otherwise "Gemma · General".
    """
    if mode_state.is_cloud():
        return "Gemini (Cloud)"
    if model_override and model_override != settings.model_primary:
        return "Vessel Ops Medical"
    return "Gemma · General"


async def _llm_tokens(
    system: str,
    user_prompt: str,
    images: Optional[list[bytes]] = None,
    severity: str = "minor",
    model_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """Route to cloud (Google) or local (Ollama) depending on runtime mode.

    `model_override` lets medical routes pin to the Unsloth WHO fine-tune
    without affecting engine/maintenance/trivia traffic.
    """
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
            system,
            user_prompt,
            severity=severity,
            images=images,
            model_override=model_override,
        ):
            yield token


async def _llm_full_response(
    system: str,
    user_prompt: str,
) -> str:
    """Get the full response from the LLM (non-streaming)."""
    full_text = ""
    async for token in _llm_tokens(system, user_prompt):
        full_text += token
    return full_text


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

    rag_results = get_rag_engine().query("medical_protocols", ", ".join(payload.symptoms), k=2)
    has_rag = False
    if rag_results:
        has_rag = True
        user_prompt += "\nRelevant Protocol Excerpts:\n"
        for r in rag_results:
            source = r['metadata'].get('source', 'Unknown Document')
            page = r['metadata'].get('page', '?')
            user_prompt += f"- {r['text']} (Source: {source}, Page: {page})\n"

    user_prompt += "\nPlease assess and provide immediate treatment guidance."
    
    system = MEDICAL_SYSTEM
    if has_rag:
        system += CITATION_INSTRUCTIONS
    if payload.succinct:
        system += SUCCINCT_MODIFIER

    medical_override = settings.effective_medical_model
    return StreamingResponse(
        _tokens_to_sse(
            _llm_tokens(
                system,
                user_prompt,
                severity=payload.severity,
                model_override=medical_override,
            ),
            model_label=_model_label(medical_override),
        ),
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

    rag_query = f"{component.name} {component.model_number or ''} {issue_description}"
    if image_analysis:
        rag_query += f" {image_analysis.get('fault_type', '')}"

    rag_results = get_rag_engine().query("engine_manuals", rag_query, k=2)
    has_rag = False
    if rag_results:
        has_rag = True
        user_prompt += "\nRelevant Manual Excerpts:\n"
        for r in rag_results:
            source = r['metadata'].get('source', 'Unknown Manual')
            page = r['metadata'].get('page', '?')
            user_prompt += f"- {r['text']} (Source: {source}, Page: {page})\n"

    user_prompt += "\nDiagnose the fault and provide repair/safety guidance."
    
    system = ENGINE_SYSTEM
    if has_rag:
        system += CITATION_INSTRUCTIONS

    return StreamingResponse(
        _tokens_to_sse(
            _llm_tokens(system, user_prompt, images=image_bytes, severity=severity),
            model_label=_model_label(None),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Multi-turn chat with Gemma, optionally grounded in a crew member or component."""
    from backend.db.models import CrewMember, Component
    rag_engine = get_rag_engine()

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

    has_rag = False
    is_medical_turn = False
    rag_query_text = payload.messages[-1].content

    # Always pull WHO medical context for any chat — sailors at sea may not
    # have a crew member "selected" but still need grounded answers. The
    # FTS5 query is ~5ms and BM25 ranks irrelevant chunks low, so the cost
    # of an off-topic miss is negligible.
    medical_rag = rag_engine.query("medical_protocols", rag_query_text, k=3)
    if medical_rag:
        has_rag = True
        # Promote to MEDICAL_SYSTEM if no crew/component context already
        # pushed us there — RAG matches mean the user is asking medical.
        if not payload.crew_id and not payload.component_id:
            system = MEDICAL_SYSTEM
            is_medical_turn = True
        if payload.crew_id and not payload.component_id:
            is_medical_turn = True
        context_lines.append("\nRelevant WHO IMGS Excerpts:")
        for r in medical_rag:
            source = r['metadata'].get('source', 'WHO IMGS')
            page = r['metadata'].get('page', '?')
            context_lines.append(f"- {r['text']} (Source: {source}, Page: {page})")

    # Keyword fallback: clinical terms the WHO IMGS doesn't index (e.g.
    # "anhedonia") still belong on the medical fine-tune. Only triggers
    # when we're not already in an engine/maintenance context.
    if not is_medical_turn and not payload.component_id and _has_medical_intent(rag_query_text):
        system = MEDICAL_SYSTEM
        is_medical_turn = True

    if payload.component_id:
        engine_rag = rag_engine.query("engine_manuals", rag_query_text, k=2)
        if engine_rag:
            has_rag = True
            context_lines.append("\nRelevant Manual Excerpts:")
            for r in engine_rag:
                source = r['metadata'].get('source', 'Unknown Manual')
                page = r['metadata'].get('page', '?')
                context_lines.append(f"- {r['text']} (Source: {source}, Page: {page})")


    if context_lines:
        system = system + "\n\nContext for this conversation:\n" + "\n".join(context_lines)

    if has_rag:
        system += CITATION_INSTRUCTIONS

    if payload.succinct:
        system += SUCCINCT_MODIFIER

    transcript = "\n\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
        for m in payload.messages
    )
    transcript += "\n\nAssistant:"

    chat_model_override = settings.effective_medical_model if is_medical_turn else None

    return StreamingResponse(
        _tokens_to_sse(
            _llm_tokens(system, transcript, model_override=chat_model_override),
            model_label=_model_label(chat_model_override),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/trivia")
async def trivia(payload: ChatRequest):
    """Trivia game stream with Captain Sparky."""
    system = TRIVIA_SYSTEM
    
    # If no messages, start with a welcome
    if not payload.messages:
        transcript = "User: Let's play trivia!\n\nAssistant:"
    else:
        transcript = "\n\n".join(
            f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
            for m in payload.messages
        )
        transcript += "\n\nAssistant:"

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(system, transcript), model_label=_model_label(None)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/study")
async def study(payload: ChatRequest):
    """MPIC Study mode stream."""
    system = MPIC_STUDY_SYSTEM
    
    if not payload.messages:
        transcript = "User: I want to start my MPIC study session. Please give me a scenario.\n\nAssistant:"
    else:
        transcript = "\n\n".join(
            f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
            for m in payload.messages
        )
        transcript += "\n\nAssistant:"

    return StreamingResponse(
        _tokens_to_sse(_llm_tokens(system, transcript), model_label=_model_label(None)),
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
        ids = [f"{file.filename}-{c['metadata']['page']}-{uuid.uuid4().hex[:8]}" for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        # Add in batches to avoid ChromaDB limits
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            get_rag_engine().add_documents(
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
    stats = {}
    engine = get_rag_engine()
    for coll in ["medical_protocols", "engine_manuals"]:
        stats[coll] = engine.collection_stats(coll)
    return stats


@router.post("/extract-medical-info")
async def extract_medical_info(data: dict = Body(...)):
    """Use LLM to extract structured medical data from free-text/voice transcripts."""
    text = data.get("text", "")
    if not text:
        return {}
        
    system = "You are a medical data extraction assistant. Extract symptoms and vitals into a structured JSON object."
    user_prompt = f"""Extract symptoms and vitals from this maritime medical log transcript:
"{text}"

Return ONLY a JSON object with these exact keys: 
- symptoms (string, comma-separated)
- hr (integer)
- bp (string)
- temp (float)
- spo2 (integer)
- severity (one of: minor, moderate, serious, critical)

If a value is not mentioned, use null (for numbers) or an empty string (for text).
"""
    response_text = await _llm_full_response(system, user_prompt)
    
    # Try to extract JSON block from potentially verbose LLM output
    try:
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception:
        pass
        
    return {"raw_response": response_text}
