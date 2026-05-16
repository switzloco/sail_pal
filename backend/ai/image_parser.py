"""
Multimodal image parser — Phase 2.

Uses Gemma 4's native vision capability via Ollama (or Google GenAI) to convert a component
photo into a structured fault description before RAG retrieval.

Two-pass flow:
  Pass 1: image → { fault_type, affected_parts, confidence }
  Pass 2: fault JSON + RAG chunks → actionable maintenance guidance
"""
import json
from typing import Optional
from backend.ai import mode_state
from backend.config import settings


async def parse_component_image(image_bytes: bytes, component_name: str) -> Optional[dict]:
    """Phase 2 implementation: Extract JSON struct from image."""
    prompt = f"Analyze this image of a {component_name}. Return ONLY a JSON object with keys: 'fault_type' (string), 'affected_parts' (list of strings), and 'confidence' (string like 'high', 'medium', 'low'). Do not include any markdown formatting or extra text."
    
    result_text = ""
    if mode_state.is_cloud():
        from backend.ai.google_client import GoogleSimulationClient
        client = GoogleSimulationClient(
            api_key=settings.google_api_key,
            model=settings.cloud_model,
        )
        try:
            async for chunk in client.chat_stream(
                system="You are a strict JSON-only image analysis tool.",
                user_prompt=prompt,
                images=[image_bytes]
            ):
                result_text += chunk
        except Exception:
            pass
    else:
        from backend.ai.ollama_client import OllamaRouter
        client = OllamaRouter(
            host=settings.ollama_host,
            model_primary=settings.model_primary,
            model_scale=settings.model_scale,
            model_fallback=settings.model_fallback,
        )
        try:
            async for chunk in client.chat_stream(
                system="You are a strict JSON-only image analysis tool.",
                user_prompt=prompt,
                images=[image_bytes],
                severity="minor"
            ):
                result_text += chunk
        except Exception:
            pass
            
    try:
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        return json.loads(result_text.strip())
    except Exception:
        return None
