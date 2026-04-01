import asyncio
from typing import Callable, Dict, List


class ResponseStreamer:
    async def stream_provider(
        self,
        provider,
        messages: List[Dict[str, str]],
        model: str,
        on_token: Callable[[str], None],
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        parts: List[str] = []
        async for tok in provider.stream_generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            parts.append(tok)
            on_token(tok)
            await asyncio.sleep(0)
        return "".join(parts)

    async def stream_text(
        self,
        text: str,
        on_token: Callable[[str], None],
        chunk_size: int = 48,
    ) -> str:
        if not text:
            return ""
        for start in range(0, len(text), chunk_size):
            chunk = text[start : start + chunk_size]
            on_token(chunk)
            await asyncio.sleep(0)
        return text
