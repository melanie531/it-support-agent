# PR #1 Review — `feat: implement RAG-powered IT support agent`

**Reviewer:** Plato 🏛️  
**Date:** 2026-04-09  
**Verdict:** REQUEST_CHANGES — 2 blocking bugs must be fixed before merge

---

## 🚫 Blocking Issues (must fix)

### B1: Double retriever initialization in API lifespan
**File:** `src/it_support_agent/api.py`, lines 23-25

The `lifespan()` function creates **two separate `ITRetriever` instances**:
1. `init_retriever()` (line 24) — initializes one inside the agent module's `_retriever`
2. `_retriever = ITRetriever()` (line 25) — creates a *second* one for the API module's health checks

This **doubles memory usage** (two FAISS indexes loaded) and means the health check reports stats from a different instance than the one actually serving queries.

**Fix:** Remove the second initialization. Reuse the agent module's retriever:
```python
init_retriever()
_retriever = agent._retriever  # reuse the same instance
```

---

### B2: Agent creates a new instance on every request
**File:** `src/it_support_agent/agent.py`, `ask()` function (line 133)

`ask()` calls `create_agent()` on every invocation, which creates a new `BedrockModel` and `Agent` each time. This adds unnecessary latency and object churn per request.

**Fix:** Create the agent once (lazily) and reuse:
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
    ...
```

---

## ⚠️ Important Issues (should fix)

### I1: `top_k` parameter accepted but ignored
**File:** `api.py:79`, `agent.py`

`AskRequest` accepts `top_k` but it's never passed to the retriever. Users think they control retrieval depth but always get default 5.

**Fix:** `result = ask(request.question, top_k=request.top_k)` and update `ask()` signature.

---

### I2: JSON response parsing doesn't handle markdown fences
**File:** `agent.py:_parse_agent_response` (line 109)

LLMs frequently wrap JSON in ` ```json ... ``` ` fences. The parser does raw `json.loads(text)` which fails, falling back to raw text with no structured sources/escalation data.

**Fix:** Strip markdown fences before parsing:
```python
text = text.strip()
if text.startswith('```'):
    lines = text.split('\n')
    text = '\n'.join(lines[1:-1])
```

---

### I3: `SIMILARITY_THRESHOLD` defined but never used
**File:** `config.py:13`, `retriever.py`

Config defines `SIMILARITY_THRESHOLD = 0.3` but `retriever.search()` returns all top-K regardless of score. Low-relevance noise gets passed to the LLM.

**Fix:** Filter in `retriever.search()`:
```python
if score < SIMILARITY_THRESHOLD:
    continue
```

---

### I4: Sequential embedding in ingestion
**File:** `ingestion.py:embed_chunks` (line 82)

Each chunk is embedded with a separate Bedrock API call in a for-loop. For 100+ chunks this is very slow.

**Fix:** Use `concurrent.futures.ThreadPoolExecutor` for parallel calls or batch if Titan supports it.

---

## 💡 Suggestions (nice to have)

| # | Issue | File | Notes |
|---|-------|------|-------|
| S1 | Bare `except Exception` | `api.py:113` | Catch specific exceptions |
| S2 | No request ID in logging | `api.py` | Add middleware for request tracing |
| S3 | Fragile CLI output assertions | `test_main.py` | Assert on behavior, not exact strings |
| S4 | Missing `__main__.py` | `src/it_support_agent/` | Needed for `python -m it_support_agent` |

---

## ✅ What's Good

- Clean project structure matching spec exactly
- Test cases map 1:1 to acceptance criteria (TC-001 → TC-024)
- Proper mocking of Bedrock calls in tests
- Pydantic for request/response validation
- System prompt matches spec verbatim
- Knowledge base documents are realistic and thorough
- Lazy imports in CLI commands (fast startup)
- Good `.gitignore` excluding vector store

---

## Cross-Reference with Open Issues

| Issue | Status in this review |
|-------|----------------------|
| #2 — `SIMILARITY_THRESHOLD` unused | ✅ Covered (I3) |
| #3 — `top_k` parameter ignored | ✅ Covered (I1) |
| #4 — JSON parsing doesn't handle markdown fences | ✅ Covered (I2) |
| #5 — Agent creates new instance per request | ✅ Covered (B2) |
| #6 — Double retriever initialization | ✅ Covered (B1) |
| #7 — Sequential embedding | ✅ Covered (I4) |
| #8 — Fragile test assertion | ✅ Covered (S3) |
| #9 — Test issue from Frank | N/A — not code-related |
