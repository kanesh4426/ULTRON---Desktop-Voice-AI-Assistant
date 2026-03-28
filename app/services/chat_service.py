from __future__ import annotations

from typing import Any, Dict, List

from app.services.chat_db import ChatDatabase


class ChatService:
    """
    Chat service backed by SQLite for persistent history.
    """

    def __init__(self, db: ChatDatabase | None = None) -> None:
        self.db = db or ChatDatabase()
        self.current_chat_id: int | None = None
        self._ensure_default_chat()

    def _ensure_default_chat(self) -> None:
        chats = self.db.get_all_chats()
        if not chats:
            chat_id = self.db.create_chat("Welcome Chat")
            self.current_chat_id = chat_id
            return
        if not self.current_chat_id:
            self.current_chat_id = chats[0].get("id")

    def get_all_chats(self) -> List[Dict[str, Any]]:
        return self.db.get_all_chats()

    def switch_chat(self, chat_id: int) -> List[Dict[str, Any]]:
        self.current_chat_id = chat_id
        return self.db.get_chat_messages(chat_id, limit=100)

    def create_chat(self, name: str | None = None) -> Dict[str, Any]:
        chat_id = self.db.create_chat(name)
        if not chat_id:
            return {"success": False, "error": "Failed to create chat"}
        self.current_chat_id = chat_id
        return {
            "success": True,
            "chat_id": chat_id,
            "chat_name": name or f"Chat {chat_id}",
            "message": "New chat created successfully",
        }

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        return self.db.rename_chat(chat_id, new_name)

    def delete_chat(self, chat_id: int) -> bool:
        return self.db.delete_chat(chat_id)

    def get_current_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.current_chat_id:
            return []
        return self.db.get_chat_messages(self.current_chat_id, limit=limit)

    def add_user_message(self, text: str) -> int | None:
        if not self.current_chat_id:
            self._ensure_default_chat()
        if not self.current_chat_id:
            return None
        return self.db.add_conversation(self.current_chat_id, text)

    def add_assistant_response(self, conversation_id: int, response: str, content_type: str) -> bool:
        return self.db.update_assistant_response(conversation_id, response, content_type)
