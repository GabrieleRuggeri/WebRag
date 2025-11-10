# WebRag

WebRag is a locally run Retrieval-Augmented Generation (RAG) assistant. It ingests PDFs, DOCX, and TXT documents, builds embeddings with ModernBERT, searches the web with Tavily, and answers questions through LangChain chains backed by local Ollama models. The Streamlit UI exposes normal, web-search, and deep-research modes so users can pivot between quick answers and multi-step investigations.

## Key Features
- **Document ingestion pipeline**: pluggable extractors plus chunking/embedding utilities store content inside a lightweight JSON vector store.
- **Hybrid retrieval**: combines local knowledge with Tavily web results and a reranker powered by Transformers to curate the best evidence.
- **LLM orchestration**: LangChain prompt templates and Ollama-backed models handle rewriting, answering, and deep-research flows.
- **Persistent conversations**: Streamlit front-end logs chats into SQLite via `ChatStore`, enabling session switching and renaming.
- **Configurable runtime**: `.env` loading and structured logging make it easy to tune behavior per environment.

## Architecture Overview
```
Streamlit UI (app.py)
 ├─ ChatStore (SQLite persistence)
 ├─ QA wrapper → LLM chain (LangChain + Ollama)
 ├─ WebSearch (Tavily API client)
 ├─ DeepResearch (query reformulation + web search + reranker)
 └─ Data ingestion utilities
     ├─ text_extraction (PDF/DOCX/TXT)
     ├─ chunking_embedding (ModernBERT embeddings)
     └─ vector_store (JSON-backed store)
```

## Requirements
- Python 3.12+ (managed via [uv](https://docs.astral.sh/uv/))
- [Ollama](https://ollama.com/) running locally with the desired models pulled (e.g., `ollama pull qwen2.5:1.5b`).
- Tavily API key for web search (`TAVILY_API_KEY`).
- Optional GPU for Torch/Transformers acceleration.

## Setup
```bash
git clone <repo-url>
cd WebRag
curl -LsSf https://astral.sh/uv/install.sh | sh  # see docs for Windows/Mac alternatives
uv python install 3.12
uv venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
uv sync  # installs dependencies from pyproject.toml
```

### Configuration
Create a `.env` file (auto-loaded by `utils.env_loader`) to hold secrets and options:
```
TAVILY_API_KEY=your-key
OLLAMA_HOST=http://localhost:11434
DEBUG=true  # optional, enables verbose logging
```

## Running the App
```bash
# using uv's runner so dependencies come from the managed env
uv run streamlit run app.py
```
The UI opens in the browser. Use the sidebar to choose the conversation, toggle Web Search / Deep Research modes, and adjust model/temperature.

## Data Ingestion Workflow
1. Drop source documents into an accessible location.
2. Use the utilities in `data_ingestion/` to extract text and embeddings.
3. Persist chunks and metadata via `VectorStore`, which serializes to `data/vector_store.json`.

## Development Notes
- Linting: `pylint $(git ls-files '*.py')`
- Logging configuration lives in `utils/logging_config.py` and honors the `DEBUG` env flag.
- The reranker (`backend/reranker.py`) lazily loads Transformers weights; expect a download on first use.

## Future Ideas
- Swap the JSON vector store for a scalable database (e.g., Chroma, PGVector).
- Add automated ingestion scripts and UI controls for uploading new documents.
- Expand test coverage for the ingestion and retrieval pipelines.
