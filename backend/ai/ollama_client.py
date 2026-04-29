import base64
from typing import AsyncIterator, List, Optional

import ollama


class OllamaRouter:
    def __init__(self, host: str, model_primary: str, model_scale: str):
        self.host = host
        self.model_primary = model_primary
        self.model_scale = model_scale

    def _pick_model(self, severity: str) -> str:
        if severity in ("critical", "serious"):
            return self.model_scale
        return self.model_primary

    async def chat_stream(
        self,
        system: str,
        user_prompt: str,
        severity: str = "minor",
        images: Optional[List[bytes]] = None,
    ) -> AsyncIterator[str]:
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
