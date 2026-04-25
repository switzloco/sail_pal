"""Google AI Studio client — simulation mode only.

Routes LLM calls to gemma-4-26b-a4b-it (or configured cloud_model) via the
Gemini API. Mirrors the interface of OllamaRouter so the AI router swaps
clients with one branch.

Grounding: Google Search grounding is DISABLED by omitting the tools
parameter. This keeps response quality comparable to an offline edge model
and prevents the simulation from looking artificially smarter than reality.
"""
from __future__ import annotations

import asyncio
import threading
from typing import AsyncIterator, List, Optional

from google import genai
from google.genai import types


class GoogleSimulationClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self.model_name = model

    async def chat_stream(
        self,
        system: str,
        user_prompt: str,
        images: Optional[List[bytes]] = None,
    ) -> AsyncIterator[str]:
        """Yield response tokens from Google AI Studio.

        Runs the synchronous SDK iterator in a daemon thread and bridges it
        to the async context via an asyncio.Queue so the FastAPI event loop
        is never blocked.
        """
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def _produce() -> None:
            try:
                client = genai.Client(api_key=self._api_key)
                config = types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.7,
                    max_output_tokens=2048,
                    # tools is intentionally omitted → Google Search grounding disabled
                )

                contents: list = []
                if images:
                    for img_bytes in images:
                        contents.append(
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                        )
                contents.append(user_prompt)

                for chunk in client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
            except Exception as exc:
                loop.call_soon_threadsafe(
                    queue.put_nowait, f"\n\n[Cloud error: {exc}]"
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=_produce, daemon=True).start()

        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
