"""
Fleet Mechanic API routes.

POST /api/fleet-mechanic/marina-sync  — upload offline traces and run the eval pipeline
POST /api/fleet-mechanic/demo-sync    — generate synthetic traces and run the pipeline (demo)
GET  /api/fleet-mechanic/traces       — list all engine traces
GET  /api/fleet-mechanic/traces/{id}  — trace detail with evaluations and patches
GET  /api/fleet-mechanic/evaluations  — list evaluations (optional ?flagged_only=true)
GET  /api/fleet-mechanic/patches      — list patches (optional ?status=pending)
PATCH /api/fleet-mechanic/patches/{id}/status — approve / reject / deploy a patch
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db import models as db_models
from ..config import settings
from ..fleet_mechanic.agent import FleetMechanicAgent
from ..fleet_mechanic.arize_client import ArizePhoenixClient
from ..fleet_mechanic.models import MarinaSyncRequest, MarinaSyncReport, PatchStatus
from ..fleet_mechanic.trace_recorder import generate_demo_trace

router = APIRouter(prefix="/api/fleet-mechanic", tags=["fleet-mechanic"])


def _make_agent() -> FleetMechanicAgent:
    phoenix = ArizePhoenixClient(
        base_url=settings.phoenix_host,
        api_key=settings.arize_api_key or None,
    )
    return FleetMechanicAgent(phoenix_client=phoenix)


@router.post("/marina-sync", response_model=MarinaSyncReport)
async def marina_sync(
    request: MarinaSyncRequest,
    db: Session = Depends(get_db),
):
    """Receive offline traces from the boat and run the Fleet Mechanic pipeline."""
    # Persist traces
    db_trace_ids: list[str] = []
    for trace in request.traces:
        t = db_models.EngineTrace(
            id=str(uuid.uuid4()),
            vessel_id=str(trace.vessel_id),
            component_name=trace.component_name,
            sensor_data_json=json.dumps(trace.sensor_data.model_dump()),
            model_prompt=trace.model_prompt,
            model_response=trace.model_response,
            reasoning_steps_json=json.dumps([s.model_dump() for s in trace.reasoning_steps]),
            diagnosis=trace.diagnosis,
            model_name=trace.model_name,
            recorded_at=trace.recorded_at.replace(tzinfo=None) if trace.recorded_at.tzinfo else trace.recorded_at,
            upload_status="uploaded",
        )
        db.add(t)
        db.flush()
        db_trace_ids.append(t.id)
    db.commit()

    # Run Fleet Mechanic agent
    report = await _make_agent().process_marina_sync(request.traces, db_trace_ids)

    # Persist results
    for trace_result, db_id in zip(report.trace_results, db_trace_ids):
        phoenix_id = trace_result.get("phoenix_trace_id")
        db.query(db_models.EngineTrace).filter(
            db_models.EngineTrace.id == db_id
        ).update({"phoenix_trace_id": phoenix_id, "upload_status": "evaluated"})

        eval_ids: list[str] = []
        for ev in trace_result.get("evaluations", []):
            e = db_models.FleetEvaluation(
                id=str(uuid.uuid4()),
                trace_id=db_id,
                evaluation_type=ev["eval_type"],
                score=ev["score"],
                label=ev["label"],
                explanation=ev.get("explanation", ""),
                flagged=ev["label"] in ("fail", "warning"),
            )
            db.add(e)
            db.flush()
            eval_ids.append(e.id)

        first_eval_id = eval_ids[0] if eval_ids else None
        for patch in trace_result.get("patches", []):
            p = db_models.PromptPatch(
                id=str(uuid.uuid4()),
                trace_id=db_id,
                evaluation_id=first_eval_id,
                patch_type=patch.get("patch_type", "system_instruction"),
                original_prompt_section=patch.get("original_prompt_section", ""),
                patched_prompt_section=patch.get("patched_prompt_section", ""),
                rationale=patch.get("rationale", ""),
                agent_reasoning=patch.get("agent_reasoning", ""),
                status="pending",
            )
            db.add(p)

    db.commit()
    return report


@router.post("/demo-sync")
async def demo_marina_sync(
    vessel_id: str = "demo-vessel",
    inject_hallucination: bool = True,
    db: Session = Depends(get_db),
):
    """
    Generate realistic synthetic traces and run the full evaluation pipeline.
    inject_hallucination=True causes two of the three traces to produce bad
    diagnoses that the Fleet Mechanic should flag and patch.
    """
    traces = [
        generate_demo_trace(vessel_id, "impeller_failure", inject_hallucination=inject_hallucination, hours_ago=8.0),
        generate_demo_trace(vessel_id, "oil_pressure_low", inject_hallucination=inject_hallucination, hours_ago=4.0),
        generate_demo_trace(vessel_id, "governor_fault", inject_hallucination=False, hours_ago=1.0),
    ]
    request = MarinaSyncRequest(traces=traces)
    return await marina_sync(request, db)


@router.get("/traces")
async def list_traces(vessel_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(db_models.EngineTrace)
    if vessel_id:
        q = q.filter(db_models.EngineTrace.vessel_id == vessel_id)
    rows = q.order_by(db_models.EngineTrace.recorded_at.desc()).all()
    return [
        {
            "id": t.id,
            "vessel_id": t.vessel_id,
            "component_name": t.component_name,
            "diagnosis": t.diagnosis,
            "model_name": t.model_name,
            "recorded_at": t.recorded_at.isoformat() if t.recorded_at else None,
            "upload_status": t.upload_status,
            "phoenix_trace_id": t.phoenix_trace_id,
        }
        for t in rows
    ]


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, db: Session = Depends(get_db)):
    t = db.query(db_models.EngineTrace).filter(db_models.EngineTrace.id == trace_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {
        "id": t.id,
        "vessel_id": t.vessel_id,
        "component_name": t.component_name,
        "sensor_data": json.loads(t.sensor_data_json),
        "model_prompt": t.model_prompt,
        "model_response": t.model_response,
        "reasoning_steps": json.loads(t.reasoning_steps_json),
        "diagnosis": t.diagnosis,
        "model_name": t.model_name,
        "recorded_at": t.recorded_at.isoformat() if t.recorded_at else None,
        "upload_status": t.upload_status,
        "phoenix_trace_id": t.phoenix_trace_id,
        "evaluations": [
            {
                "id": e.id,
                "evaluation_type": e.evaluation_type,
                "score": e.score,
                "label": e.label,
                "explanation": e.explanation,
                "flagged": e.flagged,
                "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            }
            for e in t.evaluations
        ],
        "patches": [
            {
                "id": p.id,
                "patch_type": p.patch_type,
                "original_prompt_section": p.original_prompt_section,
                "patched_prompt_section": p.patched_prompt_section,
                "rationale": p.rationale,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in t.patches
        ],
    }


@router.get("/evaluations")
async def list_evaluations(flagged_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(db_models.FleetEvaluation)
    if flagged_only:
        q = q.filter(db_models.FleetEvaluation.flagged == True)  # noqa: E712
    rows = q.order_by(db_models.FleetEvaluation.evaluated_at.desc()).all()
    return [
        {
            "id": e.id,
            "trace_id": e.trace_id,
            "evaluation_type": e.evaluation_type,
            "score": e.score,
            "label": e.label,
            "explanation": e.explanation,
            "flagged": e.flagged,
            "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
        }
        for e in rows
    ]


@router.get("/patches")
async def list_patches(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(db_models.PromptPatch)
    if status:
        q = q.filter(db_models.PromptPatch.status == status)
    rows = q.order_by(db_models.PromptPatch.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "trace_id": p.trace_id,
            "patch_type": p.patch_type,
            "original_prompt_section": p.original_prompt_section,
            "patched_prompt_section": p.patched_prompt_section,
            "rationale": p.rationale,
            "agent_reasoning": p.agent_reasoning,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]


@router.patch("/patches/{patch_id}/status")
async def update_patch_status(
    patch_id: str,
    status: PatchStatus,
    db: Session = Depends(get_db),
):
    p = db.query(db_models.PromptPatch).filter(db_models.PromptPatch.id == patch_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patch not found")
    p.status = status.value
    db.commit()
    return {"id": patch_id, "status": status.value}
