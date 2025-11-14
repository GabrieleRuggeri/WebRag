# WebRag

WebRag is a self-hosted Retrieval-Augmented Generation (RAG) system that couples a Streamlit chat UI with local document ingestion, per-conversation persistence, and optional web grounding. It routes user prompts through configurable modes (plain LLM, web-enhanced, or Deep Research) so answers can combine private documents and live search data without leaving your workstation.

## Architecture schema

- **User flow**: Browser → Streamlit chat (`app.py`) → `ChatStore` (SQLite) / `backend` services → Response stream. Sidebar controls (LLM model, temperature, mode) update `st.session_state`, `st.query_params`, and conversation metadata.
- **Mode routing**:
  1. **Normal**: prompt → `backend.question_answering.QA` → `llm.OllamaLLM`.
  2. **Web search**: prompt → `backend.web_search.WebSearch` → append search snippets → `QA`.
  3. **Deep Research**: prompt → `DeepResearch.enhance_query` → `WebSearch` + `Reranker` → context + `QA`.
- **Data ingestion flow**: `data_ingestion.DocumentExtractor` → `Chunker` → `Embedder` (`SentenceTransformer`) → `data_ingestion.VectorStore` → `data/vector_store.json`.
- **Support utilities**: `utils.env_loader` + `.env`; `utils.logging_config` for DEBUG-aware logging; `utils.utilities` for streaming responses and generating conversation titles.

Browser/Streamlit UI (`app.py` + `ChatStore`) feeds prompts into a dispatcher that
selects the correct mode before routing to downstream services:
  * Normal mode forwards the prompt directly to `backend.question_answering.QA`, which streams the assistant response.
  * Web Search mode enriches the query via `backend.web_search.WebSearch` before handing it to `QA`; both the Web Search path and Deep Research also invoke `backend.reranker.Reranker`.
  * Deep Research mode enhances queries with `DeepResearch.enhance_query`, then runs `WebSearch` + `Reranker` prior to `QA`.
The ingestion pipeline pulls documents from `data_ingestion.DocumentExtractor`, passes them through `Chunker`, embeds them via `embedding.embedder.SentenceTransformerEmbedder`, and stores the vectors in `data/vector_store.json`.

## Getting started

1. **Prerequisites**
   - Python 3.11+ (matching the dependencies in `requirements.txt`).
   - A running Ollama server with the models you plan to use (register/edit via `ollama run <model>` or `ollama serve` so `langchain_ollama.OllamaLLM` can hit `http://localhost:11434`).
   - A `TAVILY_API_KEY` in your shell/`.env` if you want the Web Search or Deep Research modes to work.

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   # Optional: control logging verbosity
   export DEBUG=True

   # Required for Tavily-powered search
   export TAVILY_API_KEY=sk_test_...
   ```

4. **Start the chat UI**

   ```bash
   streamlit run app.py
   ```

   The sidebar lets you choose the LLM model/temperature, create or select conversations, and toggle modes. Each conversation updates `st.query_params` with `uid`+`cid`, and every prompt/response pair is persisted into `chat_data/chat.db`.

## Ingesting your own documents

1. Drop source files under `data/` (or point the pipeline at any filesystem path).
2. Run the ingestion pipeline from a REPL or script:

   ```python
   from data_ingestion.ingestion_pipeline import IngestionPipeline

   IngestionPipeline().run("data/pdf_test.pdf")
   ```

   The pipeline extracts text/images, chunks the text, embeds each chunk via `SentenceTransformer`, and appends records to `data/vector_store.json`.

3. Inspect `data/vector_store.json` directly to see the saved metadata and embeddings (stored as lists when JSON serialises NumPy arrays). The store is seeded with a `mock_guid` entry, so the file always exists.

## Testing

- Unit tests for document extraction live in `test_data/test.py` and rely on mocked readers. Run them with:

  ```bash
  pytest test_data/test.py
  ```

  or

  ```bash
  python -m unittest test_data.test
  ```

## Notes for contributors

- `embedding/embedder.py` defaults to `nomic-ai/modernbert-embed-base`. Swap the model ID if you want a different SentenceTransformer checkpoint.
- `backend/reranker.py` uses `torch` and prefers CUDA when available but works on CPU. The boolean scores it returns are clamped to `[0,1]` via softmax on the “yes” logit.
- The app streams assistant replies word-by-word via `utils.response_stream` so the UI feels more responsive, but the full text is still appended to session state/SQLite.
- `ChatStore` (`backend/chat_store.py`) creates `chat_data` automatically and ensures conversations can be archived/renamed via helper methods. Use `store.export_csv(...)` if you need a snapshot.
- Logging is centrally configured; calling `utils.logging_config.configure_logging_from_env()` (as `app.py` and `data_ingestion/ingestion_pipeline.py` already do) keeps console/file output consistent.

## Directory cheat sheet

- `app.py`: Streamlit entry point and mode routing.
- `backend/`: QA engine, reranker, web search, Deep Research orchestration, and SQLite-backed chat store.
- `embedding/`: sentence-transformer wrapper used by ingestion and retrieval helpers.
- `data_ingestion/`: extractor + chunker + embedding + vector store + pipeline.
- `data/`: sample PDF + `vector_store.json`.
- `test_data/`: example documents plus extraction unit tests.
- `utils/`: logging, dotenv loader, streaming helpers, conversation title generator.

Deploy, ingest, and iterate—the README now captures the pieces so you can dive straight into whichever layer you want to extend.
