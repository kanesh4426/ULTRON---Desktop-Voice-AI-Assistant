from __future__ import annotations

import datetime
import os
from typing import Any, Dict, List

import chromadb
from chromadb.utils import embedding_functions
from app.services.chat_db import ChatDatabase


class ChatService:
    """
    Chat service backed by PostgreSQL for persistent history.
    """

    def __init__(self, db: ChatDatabase | None = None) -> None:
        self.db = db or ChatDatabase()
        self.current_chat_id: int | None = None
        self._ensure_default_chat()

        # Initialize ChromaDB Vector Store for RAG
        vector_store_path = os.path.join(os.getcwd(), "data", "vector_store")
        os.makedirs(vector_store_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=vector_store_path)
        
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="ultron_messages",
            embedding_function=self.embedding_fn
        )

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
        conv_id = self.db.add_conversation(self.current_chat_id, text)
        
        # Save & Embed to ChromaDB
        if conv_id:
            try:
                self.collection.add(
                    documents=[text],
                    metadatas=[{
                        "message_id": conv_id,
                        "chat_id": self.current_chat_id,
                        "sender": "user",
                        "timestamp": datetime.datetime.now().isoformat()
                    }],
                    ids=[f"conv_{conv_id}_user"]
                )
            except Exception as e:
                print(f"Vector store error (user msg): {e}")
                
        return conv_id

    def add_assistant_response(self, conversation_id: int, response: str, content_type: str) -> bool:
        success = self.db.update_assistant_response(conversation_id, response, content_type)
        if success:
            try:
                chat_id = self.current_chat_id or 0
                self.collection.add(
                    documents=[response],
                    metadatas=[{
                        "message_id": conversation_id,
                        "chat_id": chat_id,
                        "sender": "assistant",
                        "timestamp": datetime.datetime.now().isoformat()
                    }],
                    ids=[f"conv_{conversation_id}_assistant"]
                )
            except Exception as e:
                print(f"Vector store error (assistant resp): {e}")
        return success

    def search_past_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k similar past messages using semantic search."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            context_messages = []
            if results and results.get('documents') and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = results['documents'][0][i]
                    meta = results['metadatas'][0][i]
                    dist = results['distances'][0][i] if 'distances' in results else None
                    context_messages.append({
                        "text": doc,
                        "metadata": meta,
                        "distance": dist
                    })
            return context_messages
        except Exception as e:
            print(f"Semantic search error: {e}")
            return []
