from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.models.generation_request import GenerationRequest
from app.orchestration.workflow_runner import AssistantEngine
from app_access.manager import AppManager
from app.services.chat_service import ChatService
from app.utils.config import AssistantConfig


class AppController:
    """
    High-level application orchestrator that bridges UI requests to the AI engine.
    This is intentionally thin and delegates memory/storage to services.
    """

    def __init__(
        self,
        config: Optional[AssistantConfig] = None,
        chat_service: Optional[ChatService] = None,
    ) -> None:
        self.config = config or AssistantConfig.from_env()
        self.engine = AssistantEngine(self.config)
        self.chat = chat_service or ChatService()
        self.system_apps = AppManager()

    # --- Chat management -------------------------------------------------

    def load_chats(self) -> list[Dict[str, Any]]:
        return self.chat.get_all_chats()

    def switch_chat(self, chat_id: int) -> list[Dict[str, Any]]:
        return self.chat.switch_chat(chat_id)

    def create_chat(self, name: Optional[str] = None) -> Dict[str, Any]:
        return self.chat.create_chat(name)

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        return self.chat.rename_chat(chat_id, new_name)

    def delete_chat(self, chat_id: int) -> bool:
        return self.chat.delete_chat(chat_id)

    def get_current_chat_history(self, limit: int = 50) -> list[Dict[str, Any]]:
        return self.chat.get_current_chat_history(limit)

    def send_user_message(
        self,
        text: str,
        *,
        template_name: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        use_rag: bool = False,
    ) -> Dict[str, Any]:
        if not text or not text.strip():
            return self._error_response("Empty query received")

        # Basic system app command handling (open/close) before LLM.
        if self._is_app_command(text):
            result = self.system_apps.process_command(text)
            return {
                "success": result.get("success", False),
                "response": result.get("message") or result.get("error", "Command failed"),
                "should_speak": True,
                "content_type": "system",
                "command_type": "app_command",
                "chat_id": self.chat.current_chat_id,
            }

        conversation_id = self.chat.add_user_message(text)
        if conversation_id is None:
            return self._error_response("Failed to store conversation")

        req = GenerationRequest(
            user_input=text,
            template_name=template_name,
            template_vars=template_vars or {},
            use_rag=use_rag,
        )
        result = self.engine.generate(req)
        response_text = result.get("response", "") if result else ""
        if not response_text:
            response_text = "I'm currently unable to generate a response."

        content_type = self._detect_content_type(response_text)
        should_speak = len(response_text) < 500 and content_type != "code"
        self.chat.add_assistant_response(conversation_id, response_text, content_type)

        return {
            "success": True,
            "response": response_text.strip(),
            "should_speak": should_speak,
            "content_type": content_type,
            "command_type": "ai_response",
            "chat_id": self.chat.current_chat_id,
            "conversation_id": conversation_id,
        }

    def rate_response(self, rating: int, conversation_id: Optional[int] = None) -> bool:
        # Placeholder for feedback routing.
        return bool(rating)

    def test_connection(self) -> Dict[str, Any]:
        provider = self.config.provider
        key_attr = f"{provider}_api_key"
        api_key = getattr(self.config, key_attr, None)
        if not api_key:
            return {"ok": False, "message": f"{provider} API key missing"}
        return {"ok": True, "message": f"{provider} ready"}

    # --- Helpers ---------------------------------------------------------

    @staticmethod
    def _is_app_command(text: str) -> bool:
        lowered = text.strip().lower()
        if lowered.startswith(("open ", "close ", "start ", "launch ", "run ")):
            return True
            
        # Broader intent matching for polite or conversational commands
        action_words = {"open", "close", "launch", "start", "run"}
        common_apps = {
            "chrome", "browser", "spotify", "discord", "whatsapp", 
            "calculator", "notepad", "youtube", "telegram", "word", "excel"
        }
        words = set(re.findall(r'\b\w+\b', lowered))
        return bool(words.intersection(action_words) and words.intersection(common_apps))

    @staticmethod
    def _detect_content_type(response_text: str) -> str:
        if not response_text or not isinstance(response_text, str):
            return "normal"

        code_patterns = [
            r"```(?:\w+)?\s*\n[\s\S]*?```",
            r"def\s+\w+\s*\(",
            r"function\s+\w+\s*\(",
            r"class\s+\w+",
            r"import\s+[\w\.]+",
            r"from\s+[\w\.]+\s+import",
        ]
        for pattern in code_patterns:
            if re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE):
                return "code"

        content_patterns = [r"^#+\s+.+", r"^\d+\.\s+.+", r"^-\s+.+", r"^\*\s+.+"]
        for pattern in content_patterns:
            if re.search(pattern, response_text, re.MULTILINE):
                return "content"

        technical_terms = [
            "algorithm",
            "function",
            "variable",
            "loop",
            "array",
            "object",
            "class",
            "method",
            "api",
            "database",
            "server",
            "framework",
        ]
        if any(term in response_text.lower() for term in technical_terms):
            return "technical"

        return "normal"

    def _error_response(self, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "response": f"System Notice: {message}",
            "should_speak": True,
            "content_type": "system",
            "command_type": "error",
            "chat_id": self.chat.current_chat_id,
        }
