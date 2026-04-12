# CLAUDE.md — IT Support Agent

## Project Context
This is an IT FAQ answering agent deployed as a REST API on Amazon Bedrock AgentCore Runtime. Read `spec.md` for full requirements and acceptance criteria.

## Architecture

```
User → REST API (FastAPI) → Agent (Strands SDK) → LLM (Claude via Bedrock)
                                    ↓
                           Knowledge Base (local files)
```

## Coding Rules

### Language & Style
- Python 3.12+
- Use type hints on all function signatures
- Use `pydantic` for request/response models
- Use `async` handlers in FastAPI
- Follow PEP 8 with max line length 100
- Use f-strings for string formatting

### Project Structure
```
it-support-agent/
├── src/
│   └── it_support_agent/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── agent.py             # Agent setup and invocation
│       ├── knowledge/
│       │   ├── __init__.py
│       │   ├── loader.py        # Load FAQ content from files
│       │   └── retriever.py     # Search/retrieve relevant FAQ entries
│       ├── models.py            # Pydantic request/response models
│       └── config.py            # Configuration (env vars, settings)
├── knowledge-base/
│   └── *.md                     # FAQ content files (markdown)
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_retriever.py
│   └── test_knowledge_loader.py
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

### Dependencies (pyproject.toml)
- `strands-agents` — Agent framework
- `strands-agents-bedrock` — Bedrock model provider
- `fastapi` — API framework
- `uvicorn` — ASGI server
- `pydantic` — Data validation
- `pydantic-settings` — Config from env vars
- `pytest` — Testing
- `httpx` — Test client for FastAPI

### API Design
- `POST /ask` — Main endpoint. Request: `{"question": "..."}`. Response: `{"answer": "...", "sources": [...], "confidence": "high|medium|low"}`
- `GET /health` — Health check. Response: `{"status": "healthy", "version": "..."}`
- All errors return JSON: `{"error": "...", "detail": "..."}`
- Use HTTP status codes correctly (200, 400, 422, 500)

### Agent Rules
- System prompt must instruct the agent to ONLY answer from the knowledge base
- Agent must NOT hallucinate or invent IT procedures
- If no relevant FAQ entry is found, respond with a fallback message directing user to IT helpdesk
- Include source FAQ entry references in every response
- Keep responses concise and actionable

### Knowledge Base Format
- Each FAQ topic is a separate markdown file in `knowledge-base/`
- File naming: `topic-name.md` (kebab-case)
- Structure per file:
  ```markdown
  # Topic Title
  
  ## Question
  How do I ...?
  
  ## Answer
  Step-by-step answer...
  
  ## Tags
  vpn, network, connectivity
  ```

### Configuration
- All config via environment variables (12-factor)
- Use `pydantic-settings` BaseSettings class
- Required env vars:
  - `AWS_REGION` — Bedrock region
  - `MODEL_ID` — Bedrock model ID (default: `anthropic.claude-sonnet-4-20250514`)
  - `LOG_LEVEL` — Logging level (default: INFO)
  - `API_PORT` — Server port (default: 8080)
- NO hardcoded secrets, API keys, or credentials in code

### Error Handling
- Wrap agent invocation in try/except
- Log all errors with context (request ID, question snippet)
- Never expose internal stack traces to the API consumer
- Return structured error responses

### Testing Requirements
- Write tests FIRST (TDD) — see `test-cases.md`
- Use `pytest` with `httpx.AsyncClient` for API tests
- Mock Bedrock/LLM calls in unit tests (don't call real LLM in CI)
- Test the retriever independently from the agent
- Minimum coverage: all acceptance criteria from spec.md

### Docker
- Base image: `python:3.12-slim`
- Non-root user
- Health check instruction
- Expose port 8080
- Use multi-stage build if needed

### Security
- No credentials in code or config files
- Use IAM roles for Bedrock access (not API keys)
- Validate all input with Pydantic
- Sanitize user input before passing to the agent
- Rate limiting is nice-to-have for POC

## What NOT to Do
- ❌ Do not use LangChain (use Strands SDK)
- ❌ Do not set up a vector database for POC (use simple file-based retrieval)
- ❌ Do not build a UI
- ❌ Do not integrate with external ticketing systems
- ❌ Do not implement user authentication beyond basic API key
- ❌ Do not over-engineer — this is a POC for 10 users
