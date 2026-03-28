from typing import Dict, List

import httpx

from .base_provider import BaseLLMProvider


class HuggingFaceProvider(BaseLLMProvider):
    endpoint = "https://api-inference.huggingface.co/models/{model}"

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        if not self.api_key:
            return "Provider API key is missing."
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages]) + "\nassistant:"
        url = self.endpoint.format(model=model)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {"temperature": temperature, "max_new_tokens": max_tokens},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"]
            return str(data)

