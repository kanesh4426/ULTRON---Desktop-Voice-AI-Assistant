from __future__ import annotations

from typing import Any, Dict, List

import tiktoken


class TokenManager:
    """
    Manages token counting and context window sizing using a local tokenizer.
    """

    def __init__(self, model_name: str = "gpt-4"):
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Counts the number of tokens in a given string."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def get_safe_window(self, messages: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Creates a "sliding window" of messages that fits within the token limit,
        prioritizing the most recent messages.
        """
        total_tokens = 0
        safe_messages = []

        for message in reversed(messages):
            message_text = message.get("text", "")
            message_tokens = self.count_tokens(message_text)

            if total_tokens + message_tokens <= max_tokens:
                total_tokens += message_tokens
                safe_messages.insert(0, message)
            else:
                break  # Stop adding messages once the limit is exceeded

        return safe_messages