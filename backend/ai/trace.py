"""Offline AI trace capture.

Wraps a streaming token iterator so every offline inference is recorded to the
`ai_traces` table without changing the response the crew sees. The wrapper is
transparent: it yields each token straight through, accumulates the output, and
on completion writes one OpenInference-shaped row in a fresh DB session.

Why a fresh session: FastAPI closes the request's `get_db` session as soon as
the route returns, but a StreamingResponse keeps producing tokens *after* that.
So the trace writer opens its own short-lived SessionLocal at the end of the
stream. Capture failures are swallowed — observability must never break a
medical answer at sea.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from backend.db.database import SessionLocal
from backend.db.models import AITrace
from backend.logger import logger


async def traced_llm_tokens(
    token_iter: AsyncIterator[str],
    *,
    route: str,
    model_role: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    input_data: Optional[dict[str, Any]] = None,
    rag_sources: Optional[list[dict[str, Any]]] = None,
    severity: Optional[str] = None,
    crew_id: Optional[str] = None,
    vessel_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Yield tokens unchanged while recording the full inference as a trace."""
    started = datetime.utcnow()
    t0 = time.perf_counter()
    chunks: list[str] = []
    try:
        async for token in token_iter:
            chunks.append(token)
            yield token
    finally:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        output_text = "".join(chunks)
        _persist_trace(
            route=route,
            model_role=model_role,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            input_data=input_data,
            rag_sources=rag_sources,
            output_text=output_text,
            severity=severity,
            crew_id=crew_id,
            vessel_id=vessel_id,
            started=started,
            latency_ms=latency_ms,
        )


def _persist_trace(
    *,
    route: str,
    model_role: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    input_data: Optional[dict[str, Any]],
    rag_sources: Optional[list[dict[str, Any]]],
    output_text: str,
    severity: Optional[str],
    crew_id: Optional[str],
    vessel_id: Optional[str],
    started: datetime,
    latency_ms: int,
) -> Optional[str]:
    """Write one AITrace row. Returns the trace_id, or None on failure."""
    db = SessionLocal()
    try:
        trace = AITrace(
            vessel_id=vessel_id,
            crew_id=crew_id,
            route=route,
            model_role=model_role,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            input_data=json.dumps(input_data) if input_data is not None else None,
            rag_sources=json.dumps(rag_sources) if rag_sources is not None else None,
            output_text=output_text,
            severity=severity,
            latency_ms=str(latency_ms),
            # Rough token estimate — good enough for cost/latency dashboards and
            # avoids importing a tokenizer onto the edge device.
            token_count=str(max(1, len(output_text) // 4)),
            started_at=started,
            ended_at=datetime.utcnow(),
            eval_label="unevaluated",
        )
        db.add(trace)
        db.commit()
        db.refresh(trace)
        return trace.trace_id
    except Exception as exc:  # never let trace capture break the response
        logger.warning(f"AITrace capture failed for route={route}: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
        return None
    finally:
        db.close()


def trace_to_openinference(trace: AITrace) -> dict[str, Any]:
    """Render an AITrace as an OpenInference LLM span dict.

    This is the wire shape both the `/api/traces/export` endpoint and the Arize
    replay use, so the boat's export and the cloud ingest agree on one schema.
    See https://github.com/Arize-ai/openinference for the semantic conventions.
    """
    def _loads(v):
        if not v:
            return None
        try:
            return json.loads(v)
        except Exception:
            return v

    attributes = {
        "openinference.span.kind": "LLM",
        "llm.model_name": trace.model_name,
        "llm.system": trace.system_prompt,
        "input.value": trace.user_prompt,
        "output.value": trace.output_text,
        "metadata": {
            "route": trace.route,
            "model_role": trace.model_role,
            "severity": trace.severity,
            "crew_id": trace.crew_id,
            "vessel_id": trace.vessel_id,
            "input_data": _loads(trace.input_data),
            "rag_sources": _loads(trace.rag_sources),
            "latency_ms": trace.latency_ms,
        },
    }
    return {
        "trace_id": trace.trace_id,
        "span_id": trace.span_id,
        "name": f"{trace.route}.inference",
        "start_time": trace.started_at.isoformat() if trace.started_at else None,
        "end_time": trace.ended_at.isoformat() if trace.ended_at else None,
        "attributes": attributes,
    }
