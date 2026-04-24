from __future__ import annotations

import datetime
import os
import time
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


class ChatDatabase:
    """
    PostgreSQL-backed chat store.
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        # Defaults to a local postgres instance if env variable is missing
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ultron_memory")
        self._init_database()
        self._upgrade_database_schema()

    def get_connection(self):
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
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
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL DEFAULT 'New Chat',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        chat_id INTEGER NOT NULL,
                        user_input TEXT,
                        assistant_response TEXT,
                        content_type VARCHAR(50) DEFAULT 'normal',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            except psycopg2.Error:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

    def _upgrade_database_schema(self) -> None:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='conversations'
                """
            )
            columns = [row["column_name"] for row in cursor.fetchall()]
            if "content_type" not in columns:
                cursor.execute(
                    "ALTER TABLE conversations ADD COLUMN content_type VARCHAR(50) DEFAULT 'normal'"
                )
            # Add summary column to chats table if it doesn't exist
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='chats' AND column_name='summary'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE chats ADD COLUMN summary TEXT"
                )
                conn.commit()
            conn.close()
        except psycopg2.Error:
            return

    def create_chat(self, chat_name: Optional[str] = None) -> Optional[int]:
        try:
            if not chat_name:
                chat_name = f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chats (name) VALUES (%s) RETURNING id", (chat_name,))
            chat_id = cursor.fetchone()["id"]
            conn.commit()
            conn.close()
            return chat_id
        except psycopg2.Error:
            return None

    def get_all_chats(self) -> List[Dict[str, Any]]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, created_at, updated_at
                FROM chats
                WHERE is_active = TRUE
                ORDER BY updated_at DESC
                """
            )
            chats = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return chats
        except psycopg2.Error:
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
                    to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as iso_timestamp
                FROM conversations
                WHERE chat_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
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
        except psycopg2.Error:
            return []

    def add_conversation(self, chat_id: int, user_input: str, content_type: str = "normal") -> Optional[int]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (chat_id, user_input, content_type)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (chat_id, user_input, content_type),
            )
            conversation_id = cursor.fetchone()["id"]
            cursor.execute(
                "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (chat_id,),
            )
            conn.commit()
            conn.close()
            return conversation_id
        except psycopg2.Error:
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
                SET assistant_response = %s, content_type = %s
                WHERE id = %s
                """,
                (assistant_response, content_type, conversation_id),
            )
            cursor.execute(
                """
                UPDATE chats
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT chat_id FROM conversations WHERE id = %s)
                """,
                (conversation_id,),
            )
            conn.commit()
            conn.close()
            return True
        except psycopg2.Error:
            return False

    def get_chat_summary(self, chat_id: int) -> Optional[str]:
        """Retrieves the summary for a given chat."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT summary FROM chats WHERE id = %s", (chat_id,))
            result = cursor.fetchone()
            conn.close()
            return result["summary"] if result else None
        except psycopg2.Error:
            return None

    def update_chat_summary(self, chat_id: int, summary: str) -> bool:
        """Updates the summary for a given chat."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE chats
                SET summary = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (summary, chat_id),
            )
            conn.commit()
            conn.close()
            return True
        except psycopg2.Error:
            return False

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chats SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (new_name, chat_id),
            )
            conn.commit()
            conn.close()
            return True
        except psycopg2.Error:
            return False

    def delete_chat(self, chat_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chats SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (chat_id,),
            )
            conn.commit()
            conn.close()
            return True
        except psycopg2.Error:
            return False
