"""Vessel Ops Medical Triage Agent.

A multi-step agent (not a chatbot) that works a plan and finishes the job,
with a human MPIC kept in the loop. For each case it:

  1. PLAN      — lay out the steps it will take
  2. lookup_crew_member   (TOOL)      — pull the patient record from the DB
  3. retrieve_protocol    (RETRIEVER) — WHO IMGS / Ship Captain's Guide via RAG
  4. assess_patient       (LLM)       — grounded assessment + treatment plan
  5. evaluate_guidance    (EVALUATOR) — Arize groundedness guardrail; one
                                         stricter regeneration if it fails
  6. log_health_event     (TOOL)      — write the result to the health record

Every step is wrapped in an OpenInference span (see ``ai/tracing.py``) so the
whole reasoning trace lands in Arize AX / Phoenix. Each step is also emitted as
a structured event so the frontend can render the agent's progress live.

The agent streams ``dict`` events; the router serialises them to SSE.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.ai import tracing
from backend.ai.evals import evaluate_groundedness
from backend.ai.llm import llm_tokens
from backend.ai.prompt_templates import (
    CITATION_INSTRUCTIONS,
    MEDICAL_AGENT_SYSTEM,
    SUCCINCT_MODIFIER,
)
from backend.config import settings

_VALID_SEVERITY = {"minor", "moderate", "serious", "critical"}

# The plan the agent advertises up front — its "multi-step mission".
PLAN_STEPS = [
    {"tool": "lookup_crew_member", "label": "Review patient record"},
    {"tool": "retrieve_protocol", "label": "Retrieve WHO IMGS protocol"},
    {"tool": "assess_patient", "label": "Draft grounded assessment"},
    {"tool": "evaluate_guidance", "label": "Run Arize groundedness check"},
    {"tool": "log_health_event", "label": "Log to health record"},
]


def _rag_engine():
    # Lazy import keeps RAG (and its DB bootstrap) off the import path for tests
    # that never touch the agent.
    from backend.routers.ai import get_rag_engine

    return get_rag_engine()


class MedicalTriageAgent:
    """Orchestrates the medical triage tools under a single agent trace."""

    def __init__(self, db: Session):
        self.db = db

    # ── Tools ────────────────────────────────────────────────────────────────

    def lookup_crew_member(self, crew_id: str) -> Optional[Dict[str, Any]]:
        from backend.db.models import CrewMember

        with tracing.span(
            "tool.lookup_crew_member", kind=tracing.TOOL, input_value=crew_id
        ) as span:
            crew = (
                self.db.query(CrewMember)
                .filter(CrewMember.crew_id == crew_id)
                .first()
            )
            if not crew:
                span.set_output("not found")
                return None
            allergies = crew.allergies
            if isinstance(allergies, str):
                try:
                    allergies = json.loads(allergies or "[]")
                except json.JSONDecodeError:
                    allergies = []
            record = {
                "crew_id": crew.crew_id,
                "vessel_id": crew.vessel_id,
                "full_name": crew.full_name,
                "role": crew.role,
                "blood_type": crew.blood_type,
                "allergies": allergies or [],
                "medical_notes": crew.medical_notes,
            }
            span.set_output(json.dumps(record))
            return record

    def retrieve_protocol(self, symptoms: List[str], k: int = 3) -> List[Dict[str, Any]]:
        query = ", ".join(symptoms)
        with tracing.span(
            "tool.retrieve_protocol", kind=tracing.RETRIEVER, input_value=query
        ) as span:
            results = _rag_engine().query("medical_protocols", query, k=k)
            span.set("retrieval.documents.count", len(results))
            span.set_output(json.dumps([r.get("text", "")[:200] for r in results]))
            return results

    def log_health_event(
        self,
        *,
        patient: Dict[str, Any],
        logged_by: str,
        symptoms: List[str],
        vitals: Optional[Dict[str, Any]],
        severity: str,
        guidance: str,
        protocol_used: Optional[str],
        eval_passed: bool,
    ) -> str:
        from backend.db.models import HealthEvent

        with tracing.span("tool.log_health_event", kind=tracing.TOOL) as span:
            event = HealthEvent(
                vessel_id=patient["vessel_id"],
                crew_id=patient["crew_id"],
                logged_by=logged_by or patient["crew_id"],
                event_time=datetime.utcnow(),
                symptoms=json.dumps(symptoms or []),
                vital_signs=json.dumps(vitals) if vitals else None,
                ai_response=guidance,
                protocol_used=protocol_used,
                severity=severity if severity in _VALID_SEVERITY else "moderate",
                follow_up_required=not eval_passed,
                photo_paths=json.dumps([]),
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            span.set_output(event.event_id)
            return event.event_id

    # ── Generation ───────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        patient: Dict[str, Any],
        symptoms: List[str],
        severity: str,
        vitals: Optional[Dict[str, Any]],
        excerpts: List[Dict[str, Any]],
        stricter: bool = False,
    ) -> str:
        lines = [
            f"Patient: {patient['full_name']}, {patient['role']}",
            f"Severity: {severity.upper()}",
            f"Symptoms: {', '.join(symptoms)}",
        ]
        if patient.get("allergies"):
            lines.append(f"Known allergies: {', '.join(patient['allergies'])}")
        if patient.get("medical_notes"):
            lines.append(f"Medical notes: {patient['medical_notes']}")
        if vitals:
            lines.append(f"Vitals: {vitals}")
        if excerpts:
            lines.append("\nRetrieved protocol excerpts:")
            for r in excerpts:
                meta = r.get("metadata", {}) or {}
                source = meta.get("source", "WHO IMGS")
                page = meta.get("page", "?")
                lines.append(f"- {r.get('text', '')} (Source: {source}, p. {page})")
        if stricter:
            lines.append(
                "\nIMPORTANT: A safety check flagged unsupported claims in your previous "
                "draft. Use ONLY the excerpts above. If a detail is not in them, say so and "
                "recommend TMAS contact instead of stating it."
            )
        lines.append("\nAssess the patient and provide immediate treatment guidance.")
        return "\n".join(lines)

    async def _assess(
        self,
        prompt: str,
        severity: str,
        succinct: bool,
        has_rag: bool,
    ) -> AsyncIterator[str]:
        system = MEDICAL_AGENT_SYSTEM
        if has_rag:
            system += CITATION_INSTRUCTIONS
        if succinct:
            system += SUCCINCT_MODIFIER
        async for token in llm_tokens(
            system,
            prompt,
            severity=severity,
            model_override=settings.effective_medical_model,
        ):
            yield token

    # ── Orchestration ────────────────────────────────────────────────────────

    async def run(
        self,
        *,
        crew_id: str,
        symptoms: List[str],
        severity: str,
        vitals: Optional[Dict[str, Any]] = None,
        logged_by: Optional[str] = None,
        succinct: bool = True,
        auto_log: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Run the full triage mission, yielding structured step events."""
        with tracing.span(
            "medical_triage_agent",
            kind=tracing.AGENT,
            input_value=f"{', '.join(symptoms)} (severity={severity})",
        ) as agent_span:
            # 1. PLAN
            yield {"type": "plan", "steps": PLAN_STEPS}

            # 2. lookup_crew_member
            patient = self.lookup_crew_member(crew_id)
            if not patient:
                yield {"type": "error", "message": "Crew member not found"}
                return
            yield {
                "type": "tool_result",
                "tool": "lookup_crew_member",
                "summary": f"{patient['full_name']} ({patient['role']})",
            }

            # 3. retrieve_protocol
            excerpts = self.retrieve_protocol(symptoms)
            has_rag = bool(excerpts)
            sources = [
                {
                    "source": (e.get("metadata", {}) or {}).get("source", "WHO IMGS"),
                    "page": (e.get("metadata", {}) or {}).get("page", "?"),
                }
                for e in excerpts
            ]
            yield {
                "type": "tool_result",
                "tool": "retrieve_protocol",
                "count": len(excerpts),
                "sources": sources,
            }

            # 4. assess_patient (streamed)
            prompt = self._build_prompt(patient, symptoms, severity, vitals, excerpts)
            guidance = ""
            yield {"type": "assess_start"}
            async for token in self._assess(prompt, severity, succinct, has_rag):
                guidance += token
                yield {"type": "token", "token": token}

            # 5. evaluate_guidance (Arize groundedness guardrail)
            presentation = f"{', '.join(symptoms)} (severity {severity})"
            verdict = await evaluate_groundedness(presentation, guidance, excerpts)
            yield {"type": "eval", **verdict}

            # One stricter regeneration if the guardrail failed.
            if not verdict["passed"]:
                yield {"type": "regenerate", "reason": verdict["explanation"]}
                strict_prompt = self._build_prompt(
                    patient, symptoms, severity, vitals, excerpts, stricter=True
                )
                guidance = ""
                yield {"type": "assess_start", "attempt": 2}
                async for token in self._assess(
                    strict_prompt, severity, succinct, has_rag
                ):
                    guidance += token
                    yield {"type": "token", "token": token}
                verdict = await evaluate_groundedness(presentation, guidance, excerpts)
                yield {"type": "eval", **verdict, "attempt": 2}

            agent_span.set_output(guidance)

            # 6. log_health_event
            event_id = None
            if auto_log:
                protocol_used = sources[0]["source"] if sources else None
                event_id = self.log_health_event(
                    patient=patient,
                    logged_by=logged_by or crew_id,
                    symptoms=symptoms,
                    vitals=vitals,
                    severity=severity,
                    guidance=guidance,
                    protocol_used=protocol_used,
                    eval_passed=verdict["passed"],
                )
                yield {
                    "type": "tool_result",
                    "tool": "log_health_event",
                    "event_id": event_id,
                    "follow_up_required": not verdict["passed"],
                }

            yield {
                "type": "done",
                "event_id": event_id,
                "eval_passed": verdict["passed"],
            }
