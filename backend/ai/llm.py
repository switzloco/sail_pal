"""Shared LLM routing for Vessel Ops AI.

Single place that decides cloud (Google AI Studio) vs local (Ollama) and
emits OpenInference LLM spans so every model call shows up in Arize. The
router (`routers/ai.py`) and the medical triage agent (`ai/agent.py`) both
call through here, which keeps tracing consistent across the app.
"""
from __future__ import annotations

from typing import AsyncIterator, List, Optional

from backend.ai import mode_state, tracing
from backend.config import settings


async def llm_tokens(
    system: str,
    user_prompt: str,
    images: Optional[List[bytes]] = None,
    severity: str = "minor",
    model_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream tokens from the active backend (cloud or local).

    `model_override` lets medical routes pin to the Unsloth WHO fine-tune
    without affecting engine/maintenance traffic. The whole generation is
    wrapped in an OpenInference LLM span for Arize observability.
    """
    is_cloud = mode_state.is_cloud()
    model_name = (
        settings.cloud_model
        if is_cloud
        else (model_override or settings.model_primary)
    )

    with tracing.span(
        "llm.generate",
        kind=tracing.LLM,
        input_value=user_prompt,
    ) as span:
        span.set(tracing.LLM_MODEL_NAME, model_name)
        span.set(tracing.LLM_PROVIDER, "google" if is_cloud else "ollama")
        span.set("llm.system", system[:2000])

        collected: List[str] = []
        if is_cloud:
            from backend.ai.google_client import GoogleSimulationClient

            client = GoogleSimulationClient(
                api_key=settings.google_api_key,
                model=settings.cloud_model,
            )
            async for token in client.chat_stream(system, user_prompt, images=images):
                collected.append(token)
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
                collected.append(token)
                yield token

        span.set_output("".join(collected))


async def llm_complete(
    system: str,
    user_prompt: str,
    model_override: Optional[str] = None,
) -> str:
    """Collect a full (non-streaming) response from the active backend."""
    full_text = ""
    async for token in llm_tokens(system, user_prompt, model_override=model_override):
        full_text += token
    return full_text
