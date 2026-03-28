from pathlib import Path
import sys

# Allow running this file directly from examples/ in IDEs.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.orchestration.workflow_runner import AssistantEngine
from app.models.generation_request import GenerationRequest
from app.utils.config import AssistantConfig


def main():
    config = AssistantConfig.from_env(str(PROJECT_ROOT))
    engine = AssistantEngine(config)

    # Build/update RAG index from local docs.
    ingest_result = engine.ingest_documents("data")
    print("RAG ingest:", ingest_result)

    # Basic generation
    req = GenerationRequest(
        user_input="Explain how this assistant architecture works.",
        use_rag=True,
        rag_top_k=3,
    )
    result = engine.generate(req)
    print("\n=== RESPONSE ===")
    print(result["response"])

    # Tool example
    tool_req = GenerationRequest(user_input="list dir .")
    tool_result = engine.generate(tool_req)
    print("\n=== TOOL-AUGMENTED RESPONSE ===")
    print(tool_result["response"])

    # Streaming example
    print("\n=== STREAM ===")
    stream_req = GenerationRequest(user_input="Give a short summary of this project.")

    def on_token(tok: str):
        print(tok, end="", flush=True)

    engine.generate_stream_sync(stream_req, on_token=on_token)
    print("\n")


if __name__ == "__main__":
    from ultron import main as ultron_main

    sys.exit(ultron_main(["example"]))
