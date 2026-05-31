"""Arize ingestion for the Fleet Mechanic.

Replays stored offline traces into Arize as OpenInference LLM spans, and
attaches the Gemini eval verdict as span attributes so the hallucination
breakdown shows up in the Arize UI.

The `arize-otel` / `openinference` / `opentelemetry` packages are OPTIONAL —
they're only needed dockside. Every import is guarded so the offline edge
build (and the test suite) runs without them. Call `is_available()` before
expecting anything to actually reach Arize.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.config import settings
from backend.db.models import AITrace
from backend.ai.trace import trace_to_openinference
from backend.logger import logger

try:  # optional, dockside-only dependencies
    from arize.otel import register as _arize_register
    from opentelemetry.trace import Status, StatusCode
    _ARIZE_IMPORTED = True
except Exception:  # pragma: no cover - depends on optional install
    _arize_register = None
    Status = StatusCode = None  # type: ignore
    _ARIZE_IMPORTED = False

_tracer = None


def is_available() -> bool:
    """True when the SDK is installed AND credentials are configured."""
    return _ARIZE_IMPORTED and settings.arize_enabled


def get_tracer():
    """Lazily register the Arize OTLP tracer. Returns None if unavailable."""
    global _tracer
    if not is_available():
        return None
    if _tracer is None:
        tracer_provider = _arize_register(
            space_id=settings.arize_space_id,
            api_key=settings.arize_api_key,
            project_name=settings.arize_project_name,
        )
        _tracer = tracer_provider.get_tracer("fleet-mechanic")
    return _tracer


def _flatten_attributes(span_dict: dict[str, Any]) -> dict[str, Any]:
    """OpenInference attrs must be flat scalars/strings — JSON nested objects."""
    import json

    flat: dict[str, Any] = {}
    for key, value in span_dict["attributes"].items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, default=str)
        elif value is not None:
            flat[key] = value
    return flat


def replay_trace_to_arize(trace: AITrace) -> bool:
    """Emit one AITrace as an OpenInference span with its eval verdict attached.

    Returns True if a span was sent, False if Arize is unavailable (so the
    caller can record `uploaded_to_arize` accurately).
    """
    tracer = get_tracer()
    if tracer is None:
        return False

    span_dict = trace_to_openinference(trace)
    attributes = _flatten_attributes(span_dict)

    with tracer.start_as_current_span(span_dict["name"]) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        # Attach the eval verdict using the OpenInference eval convention so
        # Arize renders a hallucination breakdown over the medical traces.
        if trace.eval_label and trace.eval_label != "unevaluated":
            span.set_attribute("eval.hallucination.label", trace.eval_label)
            if trace.eval_score is not None:
                span.set_attribute("eval.hallucination.score", trace.eval_score)
            if trace.eval_explanation:
                span.set_attribute("eval.hallucination.explanation", trace.eval_explanation)
            if trace.eval_label in ("hallucinated", "unsafe", "unsupported"):
                span.set_status(Status(StatusCode.ERROR, trace.eval_label))
    return True


def replay_traces(traces: list[AITrace]) -> int:
    """Replay a batch of traces. Returns the number actually sent to Arize."""
    if not is_available():
        logger.info(
            "Arize unavailable (SDK installed=%s, creds=%s) — skipping upload of %d trace(s)",
            _ARIZE_IMPORTED, settings.arize_enabled, len(traces),
        )
        return 0
    sent = 0
    for trace in traces:
        try:
            if replay_trace_to_arize(trace):
                sent += 1
        except Exception as exc:  # pragma: no cover - network/SDK runtime
            logger.warning("Failed to replay trace %s to Arize: %s", trace.trace_id, exc)
    return sent
