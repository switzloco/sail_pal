import base64
from typing import AsyncIterator, List, Optional

import ollama


class OllamaRouter:
    def __init__(self, host: str, model_primary: str, model_scale: str, model_fallback: str = "gemma4:e2b"):
        self.host = host
        self.model_primary = model_primary
        self.model_scale = model_scale
        self.model_fallback = model_fallback
        self._resolved_primary: Optional[str] = None

    def _pick_model(self, severity: str) -> str:
        if severity in ("critical", "serious"):
            return self.model_scale
        return self._resolved_primary or self.model_primary

    async def _resolve_primary(self) -> str:
        """Return model_primary if it's pulled, otherwise fall back to model_fallback."""
        if self._resolved_primary:
            return self._resolved_primary
        client = ollama.AsyncClient(host=self.host)
        try:
            models = await client.list()
            names = {m.model for m in models.models}
            if self.model_primary in names:
                self._resolved_primary = self.model_primary
            else:
                self._resolved_primary = self.model_fallback
        except Exception:
            self._resolved_primary = self.model_fallback
        return self._resolved_primary

    async def chat_stream(
        self,
        system: str,
        user_prompt: str,
        severity: str = "minor",
        images: Optional[List[bytes]] = None,
    ) -> AsyncIterator[str]:
        await self._resolve_primary()
        model = self._pick_model(severity)
        client = ollama.AsyncClient(host=self.host)

        user_msg: dict = {"role": "user", "content": user_prompt}
        if images:
            user_msg["images"] = [
                base64.b64encode(img).decode("utf-8") for img in images
            ]

        messages = [
            {"role": "system", "content": system},
            user_msg,
        ]

        async for chunk in await client.chat(
            model=model,
            messages=messages,
            stream=True,
        ):
            content = chunk["message"]["content"]
            if content:
                yield content
