from __future__ import annotations

import datetime
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChatDatabase:
    """
    SQLite-backed chat store.
    Default location: data/sqlite/ultron.db
    """

    def __init__(
        self,
        db_path: str = "data/sqlite/ultron.db",
        legacy_db_path: str = "Database/JARVIS.db",
    ) -> None:
        self.db_path = db_path
        self.legacy_db_path = legacy_db_path
        self._ensure_directory()
        self._migrate_legacy_db()
        self._init_database()
        self._upgrade_database_schema()

    def _ensure_directory(self) -> None:
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _migrate_legacy_db(self) -> None:
        if os.path.exists(self.db_path):
            return
        if os.path.exists(self.legacy_db_path):
            shutil.copy2(self.legacy_db_path, self.db_path)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_database(self) -> None:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL DEFAULT 'New Chat',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        user_input TEXT,
                        assistant_response TEXT,
                        content_type TEXT DEFAULT 'normal',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_conversations_chat_id ON conversations(chat_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_updated ON chats(updated_at)")
                conn.commit()
                conn.close()
                return
            except sqlite3.Error:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

    def _upgrade_database_schema(self) -> None:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(conversations)")
            columns = [column[1] for column in cursor.fetchall()]
            if "content_type" not in columns:
                cursor.execute(
                    "ALTER TABLE conversations ADD COLUMN content_type TEXT DEFAULT 'normal'"
                )
                conn.commit()
            conn.close()
        except sqlite3.Error:
            return

    def create_chat(self, chat_name: Optional[str] = None) -> Optional[int]:
        try:
            if not chat_name:
                chat_name = f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chats (name) VALUES (?)", (chat_name,))
            chat_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return chat_id
        except sqlite3.Error:
            return None

    def get_all_chats(self) -> List[Dict[str, Any]]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, created_at, updated_at
                FROM chats
                WHERE is_active = 1
                ORDER BY updated_at DESC
                """
            )
            chats = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return chats
        except sqlite3.Error:
            return []

    def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    user_input,
                    assistant_response,
                    content_type,
                    strftime('%Y-%m-%dT%H:%M:%SZ', timestamp) as iso_timestamp
                FROM conversations
                WHERE chat_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (chat_id, limit),
            )
            messages: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                if row["user_input"]:
                    messages.append(
                        {
                            "text": row["user_input"],
                            "sender": "user",
                            "timestamp": row["iso_timestamp"],
                            "content_type": row["content_type"] or "normal",
                        }
                    )
                if row["assistant_response"]:
                    messages.append(
                        {
                            "text": row["assistant_response"],
                            "sender": "assistant",
                            "timestamp": row["iso_timestamp"],
                            "content_type": row["content_type"] or "normal",
                        }
                    )
            conn.close()
            return messages
        except sqlite3.Error:
            return []

    def add_conversation(self, chat_id: int, user_input: str, content_type: str = "normal") -> Optional[int]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (chat_id, user_input, content_type)
                VALUES (?, ?, ?)
                """,
                (chat_id, user_input, content_type),
            )
            conversation_id = cursor.lastrowid
            cursor.execute(
                "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chat_id,),
            )
            conn.commit()
            conn.close()
            return conversation_id
        except sqlite3.Error:
            return None

    def update_assistant_response(
        self, conversation_id: int, assistant_response: str, content_type: str = "normal"
    ) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE conversations
                SET assistant_response = ?, content_type = ?
                WHERE id = ?
                """,
                (assistant_response, content_type, conversation_id),
            )
            cursor.execute(
                """
                UPDATE chats
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT chat_id FROM conversations WHERE id = ?)
                """,
                (conversation_id,),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chats SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_name, chat_id),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False

    def delete_chat(self, chat_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chats SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chat_id,),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
