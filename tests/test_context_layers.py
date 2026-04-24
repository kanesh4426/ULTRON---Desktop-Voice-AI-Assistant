import os
import sys
from pathlib import Path

# Ensure the root directory is in the sys path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.services.chat_service import ChatService
from app.services.chat_db import ChatDatabase

def test_postgresql_and_vector_layers():
    print("Initializing Database & Vector Layers (may download model on first run)...")
    # Connect to PostgreSQL using settings from .env
    db = ChatDatabase()
    chat_service = ChatService(db=db)
    
    # 1. DB Check: Relational Insertion
    print("\n--- 1. Relational DB & Vector Storage Check ---")
    user_message = "The user loves Python and building AI architectures."
    print(f"Simulating User Input: '{user_message}'")
    
    conv_id = chat_service.add_user_message(user_message)
    if conv_id:
        print(f"✅ Successfully inserted user message into PostgreSQL. Conversation ID: {conv_id}")
    else:
        print("❌ Failed to insert into PostgreSQL.")
        return
        
    assistant_response = "I will remember your favorite programming language!"
    print(f"Simulating AI Response: '{assistant_response}'")
    
    if chat_service.add_assistant_response(conv_id, assistant_response, "normal"):
        print(f"✅ Successfully updated AI response in PostgreSQL.")
    else:
        print("❌ Failed to update AI response.")
        return
        
    # 2. Vector Integration Check: Semantic Search
    print("\n--- 2. Vector Store Retrieval Check ---")
    query = "What is the user's favorite language?"
    print(f"Querying ChromaDB for: '{query}'")
    
    results = chat_service.search_past_context(query, top_k=2)
    
    success = False
    for res in results:
        print(f"  -> Found context [Distance: {res['distance']:.4f}]: {res['text']}")
        if "Python" in res['text']:
            success = True
            
    if success:
        print("\n✅ PASSED: Successfully retrieved the relevant fact using Semantic Search!")
    else:
        print("\n❌ FAILED: Failed to retrieve the correct fact from ChromaDB.")

if __name__ == "__main__":
    test_postgresql_and_vector_layers()