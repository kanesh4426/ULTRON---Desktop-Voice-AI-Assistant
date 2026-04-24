from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from app.orchestration.workflow_runner import AssistantEngine
from app.services.chat_service import ChatService
from app.services.token_manager import TokenManager
from app.models.generation_request import GenerationRequest


class ContextAssembler:
    """
    Builds the "Super-Prompt" by merging system instructions, summaries,
    RAG results, and recent history, while managing token limits and latency.
    """

    SUMMARY_THRESHOLD = 2500  # Trigger summarization when history exceeds this
    RECENT_HISTORY_TOKEN_LIMIT = 2000  # Max tokens for the sliding window
    RAG_TOP_K = 3
    RECENT_HISTORY_MESSAGE_LIMIT = 8

    def __init__(
        self,
        chat_service: ChatService,
        engine: AssistantEngine,
        token_manager: TokenManager,
    ):
        self.chat_service = chat_service
        self.engine = engine
        self.token_manager = token_manager

    def _summarize_in_background(
        self, chat_id: int, text_to_summarize: str, existing_summary: Optional[str]
    ):
        """Uses the LLM to summarize conversation history in a background thread."""
        print(f"[{threading.current_thread().name}] Starting background summarization for chat {chat_id}...")
        
        prompt = (
            f"Concisely summarize the following conversation. "
            f"If there is a previous summary, integrate it with the new information.\n\n"
            f"Previous Summary:\n{existing_summary or 'None'}\n\n"
            f"New Conversation Text:\n{text_to_summarize}"
        )

        req = GenerationRequest(user_input=prompt, task_type="summarization")
        result = self.engine.generate(req)
        
        new_summary = result.get("response")
        if new_summary:
            self.chat_service.db.update_chat_summary(chat_id, new_summary)
            print(f"[{threading.current_thread().name}] Background summarization complete for chat {chat_id}.")
        else:
            print(f"[{threading.current_thread().name}] Background summarization failed for chat {chat_id}.")

    def build_prompt(self, user_input: str) -> str:
        """
        Constructs the final prompt string for the LLM, ensuring it's under 200ms.
        """
        start_time = time.perf_counter()
        chat_id = self.chat_service.current_chat_id
        if not chat_id:
            return user_input

        # 1. Fetch all data concurrently (simulated with sequential calls for clarity)
        summary = self.chat_service.db.get_chat_summary(chat_id)
        rag_results = self.chat_service.search_past_context(user_input, top_k=self.RAG_TOP_K)
        full_history = self.chat_service.get_current_chat_history(limit=100)

        # 2. Check for summarization trigger
        history_text = "\n".join([msg.get("text", "") for msg in full_history])
        history_tokens = self.token_manager.count_tokens(history_text)

        if history_tokens > self.SUMMARY_THRESHOLD:
            # Non-blocking call to summarization
            thread = threading.Thread(
                target=self._summarize_in_background,
                args=(chat_id, history_text, summary),
                daemon=True,
            )
            thread.start()

        # 3. Apply sliding window to recent history
        recent_history = self.token_manager.get_safe_window(
            full_history[-self.RECENT_HISTORY_MESSAGE_LIMIT:],
            max_tokens=self.RECENT_HISTORY_TOKEN_LIMIT
        )

        # 4. Assemble the "Super-Prompt"
        prompt_parts = []

        # System Instructions (can be loaded from a file or config)
        prompt_parts.append("[SYSTEM INSTRUCTIONS]\nYou are ULTRON, a helpful AI assistant.")

        # Memory Summary
        if summary:
            prompt_parts.append(f"[MEMORY SUMMARY]\n{summary}")

        # RAG Results (Expert Guardrail: filter out results already in recent history)
        recent_texts = {msg.get("text") for msg in recent_history}
        relevant_recollections = [res for res in rag_results if res.get("text") not in recent_texts]
        if relevant_recollections:
            rag_context = "\n".join([f'- {res["text"]}' for res in relevant_recollections])
            prompt_parts.append(f"[RELEVANT RECOLLECTIONS]\n{rag_context}")

        # Recent Conversation History
        if recent_history:
            history_str = "\n".join([f'{msg["sender"]}: {msg["text"]}' for msg in recent_history])
            prompt_parts.append(f"[RECENT CONVERSATION]\n{history_str}")

        # Final User Input
        prompt_parts.append(f"[USER INPUT]\n{user_input}")

        final_prompt = "\n\n---\n\n".join(prompt_parts)

        end_time = time.perf_counter()
        assembly_time_ms = (end_time - start_time) * 1000
        print(f"Context assembly took {assembly_time_ms:.2f}ms.")

        if assembly_time_ms > 200:
            print(f"WARNING: Context assembly exceeded 200ms latency cap ({assembly_time_ms:.2f}ms).")

        return final_prompt