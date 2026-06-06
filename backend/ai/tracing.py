"""Arize observability for the Vessel Ops medical triage agent.

Targets **Arize AX** (cloud SaaS) when ``ARIZE_API_KEY`` + ``ARIZE_SPACE_ID``
are set, and otherwise falls back to **Arize Phoenix** (self-hosted / local,
the open-source tier) — matching the app's local/cloud dual-mode design.

Every import here is optional. The offline desktop companion ships a lean
bundle (the project deliberately avoids heavy deps), so if the observability
extras aren't installed, or tracing is disabled, *all* helpers degrade to a
no-op and the app runs exactly as before. Telemetry is a hosted-mode concern;
a laptop with no internet has nothing to phone home to.

Span attribute keys follow the OpenInference semantic conventions (stable
string keys) so traces render correctly in both Phoenix and Arize AX without
taking a hard dependency on the semconv package.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from backend.config import settings

logger = logging.getLogger("vessel_ops")

# ── OpenInference semantic-convention keys (stable strings) ──────────────────
SPAN_KIND = "openinference.span.kind"
INPUT_VALUE = "input.value"
OUTPUT_VALUE = "output.value"
LLM_MODEL_NAME = "llm.model_name"
LLM_PROVIDER = "llm.provider"

# Span kinds
AGENT = "AGENT"
CHAIN = "CHAIN"
TOOL = "TOOL"
LLM = "LLM"
RETRIEVER = "RETRIEVER"
EVALUATOR = "EVALUATOR"

_TRACER = None
_INITIALIZED = False
_ENABLED = False
_BACKEND = "disabled"


def init_tracing() -> bool:
    """Initialise the tracer once. Safe to call repeatedly. Never raises."""
    global _TRACER, _INITIALIZED, _ENABLED, _BACKEND
    if _INITIALIZED:
        return _ENABLED
    _INITIALIZED = True

    if not settings.arize_tracing_enabled:
        logger.info("Arize tracing disabled (ARIZE_TRACING_ENABLED=false).")
        return False

    try:
        if settings.arize_api_key and settings.arize_space_id:
            from arize.otel import register

            tracer_provider = register(
                space_id=settings.arize_space_id,
                api_key=settings.arize_api_key,
                project_name=settings.arize_project_name,
            )
            _BACKEND = "Arize AX"
        else:
            from phoenix.otel import register

            kwargs = {"project_name": settings.arize_project_name}
            if settings.phoenix_collector_endpoint:
                kwargs["endpoint"] = settings.phoenix_collector_endpoint
            tracer_provider = register(**kwargs)
            _BACKEND = "Arize Phoenix"

        _TRACER = tracer_provider.get_tracer("vessel-ops-medical")
        _ENABLED = True

        # Auto-instrument the Google GenAI SDK (cloud mode) when available, so
        # the underlying Gemini/Gemma calls nest inside our agent spans.
        try:
            from openinference.instrumentation.google_genai import (
                GoogleGenAIInstrumentor,
            )

            GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        except Exception:  # pragma: no cover - optional instrumentor
            pass

        logger.info(
            "Arize tracing initialised → %s (project=%s)",
            _BACKEND,
            settings.arize_project_name,
        )
    except Exception as exc:  # pragma: no cover - depends on optional extras
        logger.warning(
            "Arize tracing unavailable (%s). Continuing without observability.",
            exc,
        )
        _ENABLED = False
        _BACKEND = "disabled"

    return _ENABLED


def is_enabled() -> bool:
    return _ENABLED


def backend_name() -> str:
    return _BACKEND


class _Span:
    """Thin wrapper that no-ops when tracing is disabled."""

    __slots__ = ("_s",)

    def __init__(self, otel_span=None):
        self._s = otel_span

    def set(self, key: str, value) -> None:
        if self._s is None or value is None:
            return
        try:
            self._s.set_attribute(key, value)
        except Exception:  # pragma: no cover - defensive
            pass

    def set_output(self, value) -> None:
        self.set(OUTPUT_VALUE, str(value))


@contextmanager
def span(
    name: str,
    kind: str = CHAIN,
    input_value: Optional[object] = None,
) -> Iterator[_Span]:
    """Open an OpenInference span, or a no-op span when tracing is off."""
    if _TRACER is None:
        yield _Span(None)
        return

    with _TRACER.start_as_current_span(name) as otel_span:
        handle = _Span(otel_span)
        handle.set(SPAN_KIND, kind)
        if input_value is not None:
            handle.set(INPUT_VALUE, str(input_value))
        yield handle
