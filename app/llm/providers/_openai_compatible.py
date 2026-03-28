import json
from typing import Dict, List

import httpx

from .base_provider import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    base_url: str = ""

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        if not self.api_key:
            return "Provider API key is missing."
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ):
        if not self.api_key:
            yield "Provider API key is missing."
            return
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line.replace("data:", "", 1).strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                        delta = data["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue

