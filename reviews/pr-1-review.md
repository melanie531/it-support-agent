# PR #1 Review — feat: implement RAG-powered IT support agent

**Reviewer:** Plato 🏛️  
**Verdict:** REQUEST CHANGES (2 blockers, 5 suggestions, 4 nits)  
**Date:** 2026-04-08  

---

## ✅ What's Good

- **Spec compliance is excellent** — project structure, config values, system prompt, API schema, and CLI commands all match `spec.md` exactly.
- **Test organization** — TC-001 through TC-024 are all accounted for, plus bonus tests for `save_index`, `run_ingestion`, and CLI. Good discipline.
- **Clean module boundaries** — ingestion → retriever → agent → api → main is a clean dependency chain with no circular imports.
- **Lazy imports in CLI** — `main.py` uses deferred imports inside command handlers, keeping startup fast. Smart.
- **Error handling** — `FileNotFoundError`/`ValueError` in ingestion, graceful degraded health, JSON parse fallback in agent. All solid.
- **Sample docs** — Realistic, detailed, well-structured. These will produce good retrieval results.

---

## 🚫 Blockers (must fix before merge)

### 1. Double retriever initialization in API lifespan (bug)

**File:** `src/it_support_agent/api.py`, lines 23-26

```python
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    global _retriever
    try:
        init_retriever()           # ← creates ITRetriever, sets it in agent.py
        _retriever = ITRetriever() # ← creates SECOND ITRetriever for api.py health checks
```

`init_retriever()` already creates an `ITRetriever` and sets it as the module-level global in `agent.py`. Then `_retriever = ITRetriever()` creates a *second* instance for the API module's health checks. This means:
- Two Bedrock clients initialized
- Two FAISS index loads into memory (double RAM for the index)
- If the vector store is missing, `init_retriever()` and the second `ITRetriever()` may fail at different points, leaving the system in an inconsistent state

**Fix:** Remove the second initialization. Either have `init_retriever()` return the instance, or import the retriever from the agent module:

```python
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    global _retriever
    try:
        init_retriever()
        # Reuse the same retriever that agent.py uses
        from it_support_agent.agent import _get_retriever
        _retriever = _get_retriever()
        logger.info("IT Support Agent API started, retriever loaded.")
    except FileNotFoundError:
        logger.warning("Vector store not found — run 'ingest' first.")
        _retriever = None
    yield
```

Or better — modify `init_retriever()` to return the instance:
```python
def init_retriever(store_dir: str | None = None) -> ITRetriever:
    global _retriever
    _retriever = ITRetriever(store_dir=store_dir) if store_dir else ITRetriever()
    return _retriever
```

---

### 2. Agent creates a new instance per request (performance bug)

**File:** `src/it_support_agent/agent.py`, line 137 (`ask()` function)

```python
def ask(question: str) -> dict:
    agent = create_agent()  # ← new BedrockModel + Agent on EVERY call
    result = agent(question)
    ...
```

Every call to `ask()` constructs a new `BedrockModel` and `Agent`. For a PoC this works but:
- Unnecessary object allocation on every request
- Any future agent state (conversation memory, warm caches) would be lost between calls
- Could cause latency spikes from repeated initialization

**Fix:** Lazy singleton pattern, same as the retriever:

```python
_agent: Agent | None = None

def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent

def ask(question: str) -> dict:
    agent = _get_agent()
    result = agent(question)
    return _parse_agent_response(result)
```

---

## ⚠️ Suggestions (should fix)

### 3. `top_k` parameter accepted but never used

**File:** `src/it_support_agent/api.py`, line 82

`AskRequest` accepts `top_k` but the `/ask` endpoint calls `ask(request.question)` without forwarding it. The retriever always uses `TOP_K=5`.

**Fix:** Either wire `top_k` through the full chain:
```python
# api.py
result = ask(request.question, top_k=request.top_k)

# agent.py
def ask(question: str, top_k: int = TOP_K) -> dict:
    ...
```
Or remove `top_k` from `AskRequest` to avoid confusing API consumers who think they're controlling retrieval depth.

---

### 4. Sequential embedding in ingestion pipeline

**File:** `src/it_support_agent/ingestion.py`, lines 98-108

```python
for chunk in chunks:
    body = json.dumps({"inputText": chunk["text"]})
    response = client.invoke_model(modelId=model_id, body=body)
```

Each chunk is embedded one-at-a-time. For 5 sample docs (~50 chunks) this is fine. For a real KB with 500+ docs this will be very slow. Titan Embed v2 supports batching.

**Fix (minimal):** Add a comment: `# TODO: batch embedding calls for production workloads`

**Fix (better):** Batch into groups of 20-25 texts per API call.

---

### 5. JSON parsing fragility in agent response

**File:** `src/it_support_agent/agent.py`, lines 110-130

Claude sometimes wraps JSON in markdown fences:
```
```json
{"answer": "...", "sources": [...]}
```​
```

The current `_parse_agent_response` catches `json.JSONDecodeError` and falls back to raw text, but the fallback path returns `sources: []` — silently losing source citations.

**Fix:** Strip markdown fences before parsing:
```python
import re

# Strip optional markdown fences
text = re.sub(r'^```(?:json)?\s*', '', text.strip())
text = re.sub(r'\s*```$', '', text.strip())

try:
    parsed = json.loads(text)
    ...
```

---

### 6. `SIMILARITY_THRESHOLD` is dead code

**File:** `src/it_support_agent/config.py`, line 14

`SIMILARITY_THRESHOLD = 0.3` is defined but never imported or used anywhere.

**Fix:** Either add threshold filtering in `ITRetriever.search()`:
```python
results = [r for r in results if r["score"] >= SIMILARITY_THRESHOLD]
```
Or remove the constant to avoid confusion.

---

### 7. Agent tests don't verify tool invocation

**File:** `tests/test_agent.py`

The tests mock both `_retriever` and `Agent`, then provide canned JSON responses. This effectively tests JSON parsing, not whether the agent actually calls `retrieve_it_context`. The mock `Agent` never invokes the tool.

This is *acceptable* for unit tests (integration tests TC-025/026 cover the real path), but worth noting. Consider adding an assertion like:
```python
mock_agent_instance.assert_called_once_with("How do I reset my password?")
```
to at least verify the agent was invoked with the right question.

---

## 💡 Nits

### 8. Pin upper bounds on critical dependencies

**File:** `pyproject.toml`

Consider `strands-agents>=0.1.0,<1.0` and `faiss-cpu>=1.7.4,<2.0` to prevent breaking changes from major version bumps.

### 9. `.gitignore` — missing stray `.pyc` pattern

`__pycache__/` is covered, but some tools create stray `.pyc` files outside `__pycache__`. The existing `*.py[cod]` line actually covers this — this nit is withdrawn on closer inspection. ✅

### 10. Retriever `_embed_query` shape intent

**File:** `src/it_support_agent/retriever.py`, line 68

```python
embedding = np.array([response_body["embedding"]], dtype=np.float32)
```

The `[...]` wrapping creates shape `(1, dim)` which FAISS expects. Works fine, but a brief comment like `# Shape (1, dim) as required by faiss.search` would help readability.

### 11. Fragile assertion in CLI test

**File:** `tests/test_main.py`, line 125

```python
assert call_kwargs[1].get("port") == 9000 or call_kwargs[0][2] == 9000 or 9000 in str(call_kwargs)
```

The `9000 in str(call_kwargs)` fallback is fragile. Use:
```python
assert mock_uvicorn_run.call_args.kwargs.get("port") == 9000
```

---

## Acceptance Criteria Traceability

| AC | Status | Notes |
|----|--------|-------|
| AC-001 | ✅ | Ingestion pipeline fully implemented, tests TC-001 through TC-008 |
| AC-002 | ✅ | Retriever with FAISS search, tests TC-009/010 |
| AC-003 | ✅ | Agent uses retrieval tool, tests TC-015/018 |
| AC-004 | ✅ | Sources included in response, test TC-016 |
| AC-005 | ✅ | Escalation detection, test TC-017 |
| AC-006 | ✅ | POST /ask returns 200, test TC-019 |
| AC-007 | ✅ | POST /ask validates input (min_length=5), tests TC-020/021 |
| AC-008 | ✅ | GET /health with stats, tests TC-023/024 |
| AC-009 | ✅ | CLI ingest command, test in test_main.py |
| AC-010 | ✅ | CLI serve command, test in test_main.py |
| AC-011 | ⏳ | Need to run `pytest --cov` to verify 80%+ — looks achievable given test count |
| AC-012 | ✅ | No hardcoded secrets found; all AWS access via boto3 default chain |

---

## Summary

Fix the **2 blockers** (double retriever init, agent-per-request), address the **`top_k` passthrough** and **JSON fence stripping**, and this is ready to merge. Solid implementation overall. 👏
