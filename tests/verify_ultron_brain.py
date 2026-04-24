import os
import sys
import time
from pathlib import Path

# Ensure the root directory is in the sys path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.orchestration.app_controller import AppController
from app.services.chat_db import ChatDatabase

def run_e2e_verification():
    report_lines = []
    
    def record_result(test_name: str, status: bool, message: str = "") -> None:
        icon = "✅ PASS" if status else "❌ FAIL"
        line = f"{icon}: {test_name} - {message}"
        print(line)
        report_lines.append(line)

    print("=========================================")
    print("🤖 ULTRON BRAIN VERIFICATION SUITE 🤖")
    print("=========================================\n")
    
    print("Initializing Application Controller...")
    # Initializes Postgres, ChromaDB, TokenManager, ContextAssembler, and LLM Engine
    app = AppController()
    
    # Create a dedicated test chat to avoid polluting production logs
    chat_info = app.create_chat("E2E Stress Test Chat")
    chat_id = chat_info.get("chat_id")
    app.switch_chat(chat_id)
    
    print(f"Created dedicated test session (Chat ID: {chat_id})\n")

    try:
        # ---------------------------------------------------------
        # TEST 1: The "Long-Term Memory" Test (RAG Integration)
        # ---------------------------------------------------------
        print("--- Running Test 1: Long-Term Memory ---")
        fact = "My absolute favorite programming language is Python because of its readability."
        
        # Step 1: Insert fact
        conv_id = app.chat.add_user_message(fact)
        app.chat.add_assistant_response(conv_id, "I'll remember that Python is your favorite.", "normal")
        
        # Step 2: 20 turns of filler to push the fact out of the sliding window
        print("Simulating 20 turns of filler conversation...")
        for i in range(20):
            filler_id = app.chat.add_user_message(f"Filler question {i}: What is the weather doing today?")
            app.chat.add_assistant_response(filler_id, f"Filler answer {i}: It is currently sunny.", "normal")
            
        time.sleep(1)  # Allow local ChromaDB embeddings to settle
        
        # Step 3: Ask about the distant fact using RAG
        print("Querying the distant fact...")
        response = app.send_user_message("What was that programming language I liked?", use_rag=True)
        reply_text = response.get("response", "").lower()
        
        if "python" in reply_text:
            record_result("Long-Term Memory (RAG)", True, "Successfully retrieved distant fact using ChromaDB.")
        else:
            record_result("Long-Term Memory (RAG)", False, f"Failed to retrieve fact. LLM Answered: {reply_text}")

        # ---------------------------------------------------------
        # TEST 2 & 3: "Token Overflow" and "Latency & Threading"
        # ---------------------------------------------------------
        print("\n--- Running Test 2 & 3: Token Overflow & Latency ---")
        
        # Insert a massive payload into history to breach the 2,500 token limit
        massive_text = "This is a very long filler word. " * 600  # ~4,800 tokens
        overflow_id = app.chat.add_user_message(massive_text)
        app.chat.add_assistant_response(overflow_id, "Acknowledged massive text.", "normal")
        
        print("Sending triggering message and measuring assembly latency...")
        
        # Measure Context Assembly time
        start_time = time.perf_counter()
        prompt = app.context_assembler.build_prompt("Are you still functioning?")
        assembly_latency = (time.perf_counter() - start_time) * 1000
        
        # Verify Latency
        if assembly_latency < 500:
            record_result("Latency & Threading", True, f"Context assembled in {assembly_latency:.2f}ms (Cap is 500ms). UI remains responsive.")
        else:
            record_result("Latency & Threading", False, f"Assembly exceeded latency cap: {assembly_latency:.2f}ms.")
            
        # Verify Token Manager prevented overflow in the built prompt
        if len(prompt) < len(massive_text):
            record_result("Token Overflow (Truncation)", True, "Token manager successfully truncated the massive payload via sliding window.")
        else:
            record_result("Token Overflow (Truncation)", False, "Token manager failed to truncate history.")

        # Wait for Background Summarizer Thread
        print("Waiting for async background summarization to complete (up to 15s)...")
        summary_found = False
        for _ in range(15):
            summary = app.chat.db.get_chat_summary(chat_id)
            if summary and len(summary) > 5:
                summary_found = True
                break
            time.sleep(1)
            
        if summary_found:
            record_result("Token Overflow (Async Summary)", True, "Background thread successfully generated and saved summary to Postgres.")
        else:
            record_result("Token Overflow (Async Summary)", False, "Summary was never updated in Postgres.")

        # ---------------------------------------------------------
        # TEST 4: The "State Persistence" Test
        # ---------------------------------------------------------
        print("\n--- Running Test 4: State Persistence ---")
        # Re-instantiate AppController to simulate an application restart
        app_restart = AppController()
        history = app_restart.switch_chat(chat_id)
        
        if len(history) >= 20:
            record_result("State Persistence", True, "Successfully recovered full session history from PostgreSQL after app restart.")
        else:
            record_result("State Persistence", False, f"Failed to reload history. Found only {len(history)} messages.")
            
    finally:
        print("\n🧹 Cleaning up test artifacts...")
        app.delete_chat(chat_id)  # Cascades to delete conversations in Postgres
        try:
            # Safely remove vector documents mapped to this test chat
            app.chat.collection.delete(where={"chat_id": chat_id})
        except Exception as e:
            print(f"Warning during vector cleanup: {e}")
        
        report_path = os.path.join(project_root, "verification_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"\n📄 Final verification report saved to: {report_path}")

if __name__ == "__main__":
    run_e2e_verification()