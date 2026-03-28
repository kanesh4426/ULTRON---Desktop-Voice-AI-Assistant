from typing import Dict, List

import httpx

from .base_provider import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent?key={api_key}"
    )

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        if not self.api_key:
            return "Provider API key is missing."
        text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        url = self.endpoint.format(model=model, api_key=self.api_key)
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return str(data)
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join([p.get("text", "") for p in parts]).strip()

