# IT Support Agent — Full Specification

**Project:** IT Support Agent  
**Repo:** melanie531/it-support-agent  
**Status:** Inception Complete — Ready for Construction  
**Created:** 2025 via AIDLC Inception with Plato  

---

## 1. Problem Statement

Internal IT support teams are overwhelmed with repetitive Tier-1 questions — password resets, VPN issues, software installation, hardware requests, printer problems. Employees wait hours or days for answers that exist in runbooks and KB articles. An AI agent can instantly answer these questions by searching the IT knowledge base, providing step-by-step guidance, and escalating only when it lacks confidence.

## 2. Solution Overview

A RAG-powered IT support agent that:
- Ingests IT runbook/KB documents into a vector store
- Accepts natural language questions via a REST API
- Retrieves the most relevant KB excerpts using semantic search
- Generates grounded, step-by-step answers using an LLM with source citations
- Detects when it cannot answer confidently and recommends escalation
- Provides a health endpoint for monitoring

**This is a guidance-only agent (v1)** — it tells employees what to do but does not take automated actions (no Active Directory integration, no ticket creation automation).

## 3. Target Users

- **Primary:** Internal employees seeking IT help (all departments, non-technical to technical)
- **Secondary:** IT support staff using the agent to draft responses

## 4. Core Capabilities

### 4.1 Document Ingestion Pipeline
- Load IT runbook documents from a local directory (TXT and PDF formats)
- Split documents into chunks optimized for retrieval (semantic chunking preferred, fallback to recursive character splitting)
- Generate embeddings using Amazon Bedrock Titan Embed Text v2
- Store embeddings in a FAISS vector index with metadata (source file, page, chunk ID)
- Persist the index and metadata to disk for reuse
- CLI command: `python -m it_support_agent.main ingest`

### 4.2 Retrieval
- Accept a natural language query
- Embed the query using the same Titan model
- Search the FAISS index for top-K most similar chunks (default K=5)
- Return chunks with similarity scores and source metadata
- Format results as a context string for the LLM

### 4.3 Agent / Answer Generation
- Use Strands Agents SDK with Amazon Bedrock Claude Sonnet as the LLM
- System prompt instructs the agent to:
  - ALWAYS use the retrieval tool before answering
  - Provide step-by-step instructions when applicable
  - Cite sources (document name + section)
  - If the retrieved context doesn't contain enough information, say so explicitly and recommend contacting IT support directly
  - NEVER make up IT procedures — only use what's in the knowledge base
  - Be friendly but professional
- The agent has one tool: `retrieve_it_context(query: str) -> str`
- Confidence-based escalation: if the agent determines the question is outside its knowledge or requires human intervention (account lockouts, hardware failures, security incidents), it should flag this in the response

### 4.4 REST API
- **Framework:** FastAPI with Uvicorn
- **Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask` | POST | Submit an IT question, get an answer with sources |
| `/health` | GET | Service health, index stats (vector count, doc count) |
| `/docs` | GET | Auto-generated Swagger UI |

- **`POST /ask` request body:**
```json
{
  "question": "How do I connect to the VPN from home?",
  "top_k": 5  // optional, default 5
}
```

- **`POST /ask` response body:**
```json
{
  "answer": "To connect to the VPN from home, follow these steps: ...",
  "sources": [
    {"document": "vpn_guide.txt", "section": "Remote Access", "relevance_score": 0.92}
  ],
  "escalation": false,
  "escalation_reason": null
}
```

- **`POST /ask` response when escalation needed:**
```json
{
  "answer": "I don't have enough information to resolve an account lockout. Please contact the IT Help Desk directly.",
  "sources": [],
  "escalation": true,
  "escalation_reason": "Account lockout requires manual intervention by IT admin"
}
```

### 4.5 CLI
- `python -m it_support_agent.main ingest` — Run the ingestion pipeline
- `python -m it_support_agent.main serve` — Start the FastAPI server
- `python -m it_support_agent.main ask "question"` — Ask a one-off question from the terminal

## 5. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Standard for AI/ML, great library ecosystem |
| Agent Framework | Strands Agents SDK | Lightweight, tool-use native, Bedrock-native |
| LLM | Claude Sonnet (via Amazon Bedrock) | Strong instruction following, good at structured output |
| Embeddings | Amazon Titan Embed Text v2 (1024 dims) | Low cost, good quality, native Bedrock integration |
| Vector Store | FAISS (local, IndexFlatIP) | Simple, fast, no infrastructure needed for PoC |
| API Framework | FastAPI + Uvicorn | Async, auto-docs, Pydantic validation, production-ready |
| Package Manager | uv | Fast, modern Python package management |
| Testing | pytest + pytest-asyncio | Standard, good async support |

## 6. Project Structure

```
it-support-agent/
├── CLAUDE.md                    # Steering doc for Claude Code
├── spec.md                      # This file — full specification
├── test-cases.md                # Test scenarios and acceptance criteria
├── .claude/
│   └── rules/
│       ├── tdd-rule.md          # TDD enforcement rule
│       └── spec-compliance.md   # Spec traceability rule
├── pyproject.toml               # Dependencies and project metadata
├── src/
│   └── it_support_agent/
│       ├── __init__.py
│       ├── config.py            # All configuration constants
│       ├── ingestion.py         # Document loading, chunking, embedding, indexing
│       ├── retriever.py         # Query embedding, FAISS search, context formatting
│       ├── agent.py             # Strands agent with retrieval tool
│       ├── api.py               # FastAPI application and endpoints
│       └── main.py              # CLI entry point (ingest, serve, ask)
├── data/
│   ├── sample_docs/             # Sample IT runbook documents
│   │   ├── password_reset.txt
│   │   ├── vpn_guide.txt
│   │   ├── software_installation.txt
│   │   ├── hardware_requests.txt
│   │   └── printer_troubleshooting.txt
│   └── vector_store/            # Generated FAISS index (gitignored)
│       ├── index.faiss
│       └── metadata.json
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   ├── test_retriever.py
│   ├── test_agent.py
│   └── test_api.py
└── .gitignore
```

## 7. Configuration (config.py)

All configuration should be centralized in `config.py` with sensible defaults:

```python
# Model configuration
LLM_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024

# Retrieval configuration
CHUNK_SIZE = 512          # characters per chunk
CHUNK_OVERLAP = 50        # overlap between chunks
TOP_K = 5                 # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.3  # minimum score to include a result

# Paths
DOCS_DIR = "data/sample_docs"
VECTOR_STORE_DIR = "data/vector_store"
INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"

# API configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# LLM parameters
LLM_MAX_TOKENS = 1024
LLM_TEMPERATURE = 0.1  # Low temperature for factual accuracy
```

## 8. System Prompt

The agent's system prompt should be:

```
You are an IT Support Agent for Acme Corporation. Your job is to help employees
resolve common IT issues by searching the IT knowledge base.

RULES:
1. ALWAYS use the retrieve_it_context tool to search the knowledge base before
   answering. Never answer from your own knowledge.
2. Provide clear, step-by-step instructions when applicable.
3. Cite your sources — mention which document and section the information comes from.
4. If the knowledge base doesn't contain enough information to answer confidently,
   say so explicitly. Do NOT make up IT procedures.
5. For issues requiring human intervention (account lockouts, hardware failures,
   security incidents, access to restricted systems), recommend the employee
   contact the IT Help Desk at helpdesk@acmecorp.com or ext. 5000.
6. Be friendly and professional. Avoid jargon unless the user seems technical.
7. If the question is not related to IT support, politely redirect the employee
   to the appropriate department.

ESCALATION TRIGGERS (always recommend human help for these):
- Account lockouts or security compromises
- Hardware failures or physical damage
- Network outages affecting multiple users
- Requests for admin/root access
- Data recovery
- Security incidents or suspected breaches
```

## 9. Sample IT Documents

Create 5 realistic IT runbook documents covering:

1. **password_reset.txt** — Self-service password reset (Okta/SSO), password requirements (12+ chars, complexity rules), MFA setup and recovery, account lockout policy (5 failed attempts = 30 min lockout), who to contact if locked out
2. **vpn_guide.txt** — Cisco AnyConnect setup (Windows/Mac/Linux), connecting to VPN, split tunneling policy, common VPN errors and fixes, VPN required for: internal tools, file shares, dev environments; NOT required for: email, Slack, Zoom
3. **software_installation.txt** — Approved software list, how to request software through the IT portal (Jira Service Management), self-service installs (VS Code, Chrome, Slack, Zoom), admin-required installs (Docker, dev tools), license management, prohibited software
4. **hardware_requests.txt** — Standard equipment (laptop, monitor, peripherals), how to request new hardware, replacement policy (3-year refresh cycle), remote employee home office stipend ($500), broken equipment process, loaner devices
5. **printer_troubleshooting.txt** — Adding network printers (by floor/building), common print issues (offline, paper jam, driver errors), print queue management, scanning to email setup, toner/supply requests, which printers support duplex/color

## 10. Acceptance Criteria

| ID | Criteria | Verification |
|----|----------|-------------|
| AC-001 | Ingestion pipeline loads TXT files, chunks them, embeds via Titan, stores in FAISS | Unit test: load 5 sample docs, verify chunk count > 0, verify index.ntotal matches |
| AC-002 | Retriever returns top-K relevant chunks for a query with scores | Unit test: search for "password reset", verify results contain password_reset.txt chunks |
| AC-003 | Agent uses retrieval tool and generates grounded answer | Integration test: ask "How do I reset my password?", verify answer contains steps from KB |
| AC-004 | Agent cites sources in its response | Test: verify response includes document name reference |
| AC-005 | Agent flags escalation for out-of-scope questions | Test: ask about account lockout, verify escalation=true in response |
| AC-006 | POST /ask returns 200 with answer and sources | API test: POST valid question, check response schema |
| AC-007 | POST /ask returns 422 for invalid input (empty/short question) | API test: POST invalid body, check 422 |
| AC-008 | GET /health returns service status and index stats | API test: check 200 and expected fields |
| AC-009 | CLI ingest command processes all sample docs without error | Manual/integration test |
| AC-010 | CLI serve command starts API on configured port | Manual test |
| AC-011 | All tests pass with 80%+ coverage | pytest --cov check |
| AC-012 | No hardcoded secrets or credentials in codebase | Code review / grep check |

## 11. Out of Scope (v1)

- No automated actions (no password resets, no ticket creation, no AD integration)
- No Slack/Teams integration (API only — channel integration is v2)
- No authentication on the API (internal PoC)
- No persistent conversation history / multi-turn memory
- No feedback loop or answer rating
- No PDF ingestion (TXT only for v1 simplicity — PDF support is an easy add)

## 12. Future Enhancements (v2+)

- Slack/Teams bot integration
- Automated ticket creation in Jira Service Management
- Self-service actions (password reset via Okta API, MFA enrollment)
- Conversation memory (multi-turn support)
- User feedback collection and answer quality tracking
- PDF and Confluence ingestion
- Authentication (API key or OAuth)
- Deployment to AWS (ECS or Lambda)
