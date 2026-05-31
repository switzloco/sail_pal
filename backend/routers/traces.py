"""Fleet Mechanic API — the offline→dock→eval→patch loop.

Endpoints group into three roles:

  Boat (offline / dockside):
    GET  /api/traces/export          → traces this vessel hasn't synced yet
    POST /api/traces/{id}/mark-synced
    GET  /api/traces/patches/pending → queued patches to apply before departure
    POST /api/traces/patches/{id}/ack → mark a patch pushed to the vessel

  Marina ingest (when a vessel uploads):
    POST /api/traces                 → ingest a batch of uploaded traces

  Fleet Mechanic (cloud agent):
    POST /api/traces/evaluate        → run the Gemini eval + draft/queue patches
    GET  /api/traces                 → list traces (with eval verdicts)
    GET  /api/traces/patches         → list drafted/queued patches
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import AITrace, PromptPatch
from backend.ai.trace import trace_to_openinference
from backend.schemas.pydantic_models import (
    AITraceRead, PromptPatchRead, TraceUploadBatch, FleetMechanicRunResult,
)
from backend.logger import logger

router = APIRouter()


# ── Listing & inspection ──────────────────────────────────────────────────────

@router.get("", response_model=List[AITraceRead])
@router.get("/", response_model=List[AITraceRead])
def list_traces(
    db: Session = Depends(get_db),
    eval_label: Optional[str] = Query(None),
    route: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
):
    q = db.query(AITrace)
    if eval_label:
        q = q.filter(AITrace.eval_label == eval_label)
    if route:
        q = q.filter(AITrace.route == route)
    return q.order_by(AITrace.created_at.desc()).limit(limit).all()


@router.get("/export")
def export_traces(db: Session = Depends(get_db), include_synced: bool = False):
    """OpenInference-shaped export — the payload a vessel ships at the dock."""
    q = db.query(AITrace)
    if not include_synced:
        q = q.filter(AITrace.synced == False)  # noqa: E712
    traces = q.order_by(AITrace.created_at.asc()).all()
    return {
        "project_name": settings.arize_project_name,
        "count": len(traces),
        "spans": [trace_to_openinference(t) for t in traces],
    }


# ── Marina ingest ─────────────────────────────────────────────────────────────

@router.post("", response_model=dict)
@router.post("/", response_model=dict)
def ingest_traces(batch: TraceUploadBatch, db: Session = Depends(get_db)):
    """Ingest a batch of traces uploaded from a vessel. Idempotent on trace_id."""
    import json

    ingested, skipped = 0, 0
    for item in batch.traces:
        if item.trace_id and db.query(AITrace).filter(AITrace.trace_id == item.trace_id).first():
            skipped += 1
            continue
        trace = AITrace(
            **({"trace_id": item.trace_id} if item.trace_id else {}),
            **({"span_id": item.span_id} if item.span_id else {}),
            vessel_id=item.vessel_id,
            crew_id=item.crew_id,
            route=item.route,
            model_role=item.model_role,
            model_name=item.model_name,
            system_prompt=item.system_prompt,
            user_prompt=item.user_prompt,
            input_data=json.dumps(item.input_data) if item.input_data is not None else None,
            rag_sources=json.dumps(item.rag_sources) if item.rag_sources is not None else None,
            output_text=item.output_text,
            severity=item.severity,
            latency_ms=item.latency_ms,
            synced=True,  # arrived at the marina by definition
            eval_label="unevaluated",
        )
        db.add(trace)
        ingested += 1
    db.commit()
    return {"ingested": ingested, "skipped": skipped}


@router.post("/{trace_id}/mark-synced", response_model=AITraceRead)
def mark_synced(trace_id: str, db: Session = Depends(get_db)):
    trace = db.query(AITrace).filter(AITrace.trace_id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    trace.synced = True
    db.commit()
    db.refresh(trace)
    return trace


# ── Fleet Mechanic eval run ─────────────────────────────────────────────────────

@router.post("/evaluate", response_model=FleetMechanicRunResult)
def evaluate(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=500),
    upload_to_arize: bool = Query(True),
    only_synced: bool = Query(True),
):
    """Wake the Fleet Mechanic: grade pending traces and queue prompt patches."""
    if settings.cloud_mode is False and not settings.google_api_key:
        raise HTTPException(
            status_code=400,
            detail="Fleet Mechanic needs a Gemini API key (GOOGLE_API_KEY). It runs dockside, not on the vessel.",
        )
    from backend.eval.fleet_mechanic import run_fleet_mechanic

    summary = run_fleet_mechanic(
        db, limit=limit, upload_to_arize=upload_to_arize, only_synced=only_synced
    )
    logger.info("Fleet Mechanic run complete: %s", summary)
    return summary


# ── Prompt patches ──────────────────────────────────────────────────────────────

@router.get("/patches", response_model=List[PromptPatchRead])
def list_patches(
    db: Session = Depends(get_db), status: Optional[str] = Query(None)
):
    q = db.query(PromptPatch)
    if status:
        q = q.filter(PromptPatch.status == status)
    return q.order_by(PromptPatch.created_at.desc()).all()


@router.get("/patches/pending", response_model=List[PromptPatchRead])
def pending_patches(db: Session = Depends(get_db)):
    """Patches a vessel should pull and apply before leaving the dock."""
    return (
        db.query(PromptPatch)
        .filter(PromptPatch.status == "queued")
        .order_by(PromptPatch.queued_at.asc())
        .all()
    )


@router.post("/patches/{patch_id}/ack", response_model=PromptPatchRead)
def ack_patch(patch_id: str, db: Session = Depends(get_db)):
    """Vessel confirms it applied a patch → mark it pushed."""
    patch = db.query(PromptPatch).filter(PromptPatch.patch_id == patch_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    patch.status = "pushed"
    patch.pushed_at = datetime.utcnow()
    db.commit()
    db.refresh(patch)
    return patch


@router.post("/patches/{patch_id}/reject", response_model=PromptPatchRead)
def reject_patch(patch_id: str, db: Session = Depends(get_db)):
    patch = db.query(PromptPatch).filter(PromptPatch.patch_id == patch_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    patch.status = "rejected"
    db.commit()
    db.refresh(patch)
    return patch
