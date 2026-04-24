import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the root directory is in the sys path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.services.token_manager import TokenManager
from app.services.context_assembler import ContextAssembler


def test_token_manager_sliding_window():
    """
    Token Edge-Case: Feed an extremely long input and verify the 'Sliding Window'
    drops the oldest messages but keeps recent ones.
    """
    print("\n--- 1. Testing Token Manager Sliding Window ---")
    token_manager = TokenManager()

    # Each message is ~10 tokens. Total ~50 tokens.
    messages = [
        {"sender": "user", "text": "This is the oldest message, it should be dropped."},
        {"sender": "ai", "text": "This is an old AI response, also to be dropped."},
        {"sender": "user", "text": "This message is closer to the limit but might go."},
        {"sender": "ai", "text": "This is a more recent AI response that should stay."},
        {"sender": "user", "text": "This is the most recent message, it must be kept."},
    ]

    # Set a limit that only allows the last ~2 messages
    safe_window = token_manager.get_safe_window(messages, max_tokens=25)

    assert len(safe_window) == 2, f"Expected 2 messages, but got {len(safe_window)}"
    assert "most recent" in safe_window[1]["text"], "The most recent message was dropped"
    assert "more recent" in safe_window[0]["text"], "A recent message was dropped"
    assert "oldest" not in " ".join([m["text"] for m in safe_window]), "The oldest message was not dropped"

    print("✅ PASSED: Token manager correctly applied the sliding window.")


def test_context_assembler_format_and_latency():
    """
    Assembler Format: Verify the final string output matches the expected structure.
    Latency Cap: Verify it runs under the 200ms cap.
    """
    print("\n--- 2. Testing Context Assembler Formatting & Latency ---")
    mock_chat_service = MagicMock()
    mock_engine = MagicMock()
    token_manager = TokenManager()

    # Setup mock return values
    mock_chat_service.current_chat_id = 1
    mock_chat_service.db.get_chat_summary.return_value = "The user is interested in AI."
    mock_chat_service.search_past_context.return_value = [
        {"text": "RAG Result: AI can be built with Python."}
    ]
    mock_chat_service.get_current_chat_history.return_value = [
        {"sender": "user", "text": "Tell me about AI."},
        {"sender": "ai", "text": "AI is Artificial Intelligence."},
    ]

    assembler = ContextAssembler(mock_chat_service, mock_engine, token_manager)
    
    start_time = time.perf_counter()
    prompt = assembler.build_prompt("What else can it do?")
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000
    print(f"Assembly took {latency_ms:.2f}ms.")

    assert latency_ms < 200, f"Latency cap failed: {latency_ms:.2f}ms"
    assert "[SYSTEM INSTRUCTIONS]" in prompt
    assert "[MEMORY SUMMARY]\nThe user is interested in AI." in prompt
    assert "[RELEVANT RECOLLECTIONS]\n- RAG Result: AI can be built with Python." in prompt
    assert "[RECENT CONVERSATION]\nuser: Tell me about AI.\nai: AI is Artificial Intelligence." in prompt
    assert "[USER INPUT]\nWhat else can it do?" in prompt

    print("✅ PASSED: Context Assembler produced a correctly formatted prompt within the latency cap.")


@patch('threading.Thread.start')
def test_async_summarization_thread(mock_thread_start):
    """
    Async Thread Test: Confirm that a summarization trigger does not block the main thread.
    """
    print("\n--- 3. Testing Async Background Summarization ---")
    mock_chat_service = MagicMock()
    mock_engine = MagicMock()
    token_manager = TokenManager()

    # Create a very long history to safely exceed the 2500 token threshold
    long_history_text = "This is a very long conversation history. " * 500  # ~4000 tokens
    long_history = [{"sender": "user", "text": long_history_text}]

    mock_chat_service.current_chat_id = 1
    mock_chat_service.db.get_chat_summary.return_value = None
    mock_chat_service.search_past_context.return_value = []
    mock_chat_service.get_current_chat_history.return_value = long_history

    assembler = ContextAssembler(mock_chat_service, mock_engine, token_manager)
    assembler.build_prompt("Final question.")

    mock_thread_start.assert_called_once()
    print("✅ PASSED: Background summarization thread was correctly initiated without blocking.")


if __name__ == "__main__":
    test_token_manager_sliding_window()
    test_context_assembler_format_and_latency()
    test_async_summarization_thread()