"""
Multimodal image parser — Phase 2.

Uses Gemma 4's native vision capability via Ollama to convert a component
photo into a structured fault description before RAG retrieval.

Two-pass flow:
  Pass 1: image → { fault_type, affected_parts, confidence }
  Pass 2: fault JSON + RAG chunks → actionable maintenance guidance
"""
from typing import Optional


async def parse_component_image(image_b64: str, component_name: str) -> Optional[dict]:
    """Phase 2 implementation."""
    raise NotImplementedError("Image parsing is Phase 2")
