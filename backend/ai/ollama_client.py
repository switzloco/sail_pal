"""
Ollama client wrapper — Phase 2.

Routing logic (to be implemented):
  severity critical/serious  → attempt configured scale model (gemma4:27b),
                               fallback to primary model (gemma4:12b) on error
  severity minor/moderate    → primary model directly
  quick lookups              → primary model with reduced context window
"""
from typing import AsyncIterator, List, Optional


class OllamaRouter:
    def __init__(self, host: str, model_primary: str, model_scale: str):
        self.host = host
        self.model_primary = model_primary
        self.model_scale = model_scale

    async def chat_stream(
        self,
        messages: List[dict],
        severity: str = "minor",
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[str]:
        """Stream chat response tokens from Ollama. Phase 2 implementation."""
        raise NotImplementedError("Ollama integration is Phase 2")
