# Assistant Architecture (Refactored)

## What this package adds
- Modular assistant core with planner, tool executor, and streaming response flow.
- Multi-provider LLM abstraction for Gemini, Groq, HuggingFace, and OpenRouter.
- RAG pipeline with loader -> chunker -> embedding -> vector store -> retriever.
- Prompt template engine with file-based templates.
- Tool system (file, web search, code execution).
- PySide6 example showing token streaming in UI.

## Quick start
1. Ensure `.env` contains keys for the provider you use.
2. Run:
   - `python examples/example_usage.py`
3. PySide demo:
   - `python examples/pyside_integration_example.py`

## Provider switching
```python
engine.switch_provider("gemini", model="gemini-1.5-flash")
```

## RAG ingestion
```python
engine.ingest_documents("data")
```
