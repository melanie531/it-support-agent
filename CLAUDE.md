# CLAUDE.md — IT Support Agent

> Steering document for Claude Code. This tells you HOW to build the project.
> For WHAT to build, see `spec.md`.

## Project Overview

**What:** RAG-powered IT support agent that answers employee IT questions from a knowledge base  
**Repo:** `melanie531/it-support-agent`  
**Spec:** See `spec.md` for full requirements, architecture, and acceptance criteria  
**Test Cases:** See `test-cases.md` for detailed test scenarios  

## Build Order (STRICT — follow this sequence)

1. **Project scaffolding** — `pyproject.toml`, directory structure, `config.py`, `.gitignore`
2. **Ingestion pipeline** — `ingestion.py`: load docs → chunk → embed via Bedrock Titan → store in FAISS
3. **Retriever** — `retriever.py`: load FAISS index, embed query, search, format context
4. **Agent** — `agent.py`: Strands agent with `retrieve_it_context` tool, system prompt, `ask()` function
5. **API** — `api.py`: FastAPI app with `/ask`, `/health` endpoints and lifespan initialization
6. **CLI** — `main.py`: `ingest`, `serve`, `ask` commands using argparse or click
7. **Sample documents** — Create 5 IT runbook TXT files in `data/sample_docs/`
8. **Tests** — Write tests for each module (but prefer TDD — write tests first when implementing each stage)

## Tech Stack (DO NOT CHANGE)

- **Python 3.11+** with `uv` package manager
- **Strands Agents SDK** (`strands-agents`, `strands-agents-tools`) — agent framework
- **Amazon Bedrock** — Claude Sonnet for LLM, Titan Embed Text v2 for embeddings
- **FAISS** (`faiss-cpu`) — local vector store
- **FastAPI** + **Uvicorn** — API layer
- **pytest** + **pytest-asyncio** + **httpx** — testing

## pyproject.toml Dependencies

```toml
[project]
name = "it-support-agent"
version = "0.1.0"
description = "RAG-powered IT support agent using Strands SDK and Amazon Bedrock"
requires-python = ">=3.11"
dependencies = [
    "strands-agents>=0.1.0",
    "strands-agents-tools>=0.1.0",
    "faiss-cpu>=1.7.4",
    "fastapi>=0.115.0",
    "uvicorn>=0.34.0",
    "boto3>=1.35.0",
    "numpy>=1.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
    "pytest-cov>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/it_support_agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

## Coding Standards (ENFORCE THESE)

- **PEP 8**, max line length 120
- **Type hints** on ALL function signatures
- **Docstrings** on ALL public functions (Google style)
- **Use `pathlib.Path`** instead of `os.path`
- **No bare `except:`** — always catch specific exceptions
- **Use `logging` module**, not `print()` (except in CLI output)
- **No hardcoded secrets** — all AWS access via boto3 default credential chain
- **Configuration centralized** in `config.py` — no magic strings scattered in code

## Architecture Patterns

### Ingestion Pipeline (`ingestion.py`)
```
load_documents(dir_path: str) -> list[dict]
  - Scan directory for .txt files
  - Return list of {"text": str, "source": str, "page": int}
  - Raise FileNotFoundError if dir doesn't exist
  - Raise ValueError if no documents found

chunk_documents(docs: list[dict], chunk_size: int, chunk_overlap: int) -> list[dict]
  - Split each doc's text into overlapping chunks
  - Preserve metadata (source, page) on each chunk
  - Add sequential chunk_id
  - Return list of {"text": str, "source": str, "page": int, "chunk_id": int}

embed_chunks(chunks: list[dict], model_id: str) -> np.ndarray
  - Call Bedrock Titan for each chunk's text
  - Return numpy array of shape (n_chunks, 1024)
  - Use batch processing where possible

build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP
  - Normalize embeddings (L2 normalize for cosine similarity via inner product)
  - Create IndexFlatIP with dimension 1024
  - Add all embeddings
  - Return index

save_index(index, metadata, store_dir: str) -> None
  - Write index.faiss and metadata.json to store_dir

run_ingestion(docs_dir: str, store_dir: str) -> dict
  - Orchestrates the full pipeline
  - Returns stats: {"documents": int, "chunks": int, "vectors": int}
```

### Retriever (`retriever.py`)
```
class HRRetriever:  # (name it ITRetriever for this project)
    def __init__(self, store_dir: str = VECTOR_STORE_DIR)
    def search(self, query: str, top_k: int = TOP_K) -> list[dict]
    def format_context(self, results: list[dict]) -> str
    @property
    def document_count(self) -> int
    @property
    def vector_count(self) -> int
```

### Agent (`agent.py`)
```
@tool
def retrieve_it_context(query: str) -> str
    """Search the IT knowledge base."""

def create_agent() -> Agent
def ask(question: str) -> dict
    # Returns {"answer": str, "sources": list, "escalation": bool, "escalation_reason": str|None}
```

### API (`api.py`)
```
POST /ask  — AskRequest -> AskResponse
GET /health — HealthResponse
```

**Key detail:** The `/ask` response must include `escalation` (bool) and `escalation_reason` (str|None) fields. The agent determines escalation based on the system prompt's escalation triggers.

### CLI (`main.py`)
```
python -m it_support_agent.main ingest
python -m it_support_agent.main serve
python -m it_support_agent.main ask "How do I reset my password?"
```

## Testing Strategy

- **TDD preferred:** Write failing test → implement → make it pass → refactor
- **Unit tests:** Mock boto3/Bedrock calls, use real FAISS with synthetic embeddings
- **API tests:** Use `httpx.AsyncClient` with `ASGITransport` — no real server needed
- **Coverage target:** 80%+
- **Test file naming:** `tests/test_{module_name}.py`
- **Fixtures:** Use pytest fixtures for mock retriever, mock agent, temp directories
- See `test-cases.md` for detailed test scenarios

## System Prompt

Use the exact system prompt from `spec.md` Section 8. Do not modify it.

## Sample Documents

Create 5 realistic IT runbook documents as specified in `spec.md` Section 9. Each should be 1-3 pages of realistic content with numbered sections, step-by-step instructions, and contact information. These are the knowledge base the agent searches.

## What NOT to Build

- No authentication (v1 is internal PoC)
- No Slack/Teams integration (API only)
- No automated actions (guidance only)
- No multi-turn conversation memory
- No PDF ingestion (TXT only)
- No Docker/deployment config (local only)

## Verification Checklist

Before considering the project done:
- [ ] `uv sync` installs all dependencies without errors
- [ ] `python -m it_support_agent.main ingest` processes all 5 sample docs
- [ ] `python -m it_support_agent.main serve` starts API on port 8000
- [ ] `curl POST /ask` returns answer with sources and escalation fields
- [ ] `curl GET /health` returns status with index stats
- [ ] `pytest -v` — all tests pass
- [ ] `pytest --cov` — 80%+ coverage
- [ ] No hardcoded credentials or secrets
- [ ] All public functions have type hints and docstrings
