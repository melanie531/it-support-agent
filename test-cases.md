# IT Support Agent — Test Cases

> Detailed test scenarios mapped to acceptance criteria from `spec.md`.
> Claude Code should implement these as pytest tests.

---

## 1. Ingestion Tests (`tests/test_ingestion.py`)

### TC-001: Load TXT files from directory
**Maps to:** AC-001  
**Setup:** Create temp directory with 2+ `.txt` files containing sample text  
**Action:** Call `load_documents(tmp_dir)`  
**Assert:**
- Returns list with length == number of files
- Each item has keys: `text`, `source`, `page`
- `source` matches the filename
- `text` matches file content

### TC-002: Raise FileNotFoundError for missing directory
**Maps to:** AC-001  
**Action:** Call `load_documents("/nonexistent/path")`  
**Assert:** Raises `FileNotFoundError`

### TC-003: Raise ValueError for empty directory
**Maps to:** AC-001  
**Setup:** Create empty temp directory  
**Action:** Call `load_documents(tmp_dir)`  
**Assert:** Raises `ValueError` with message containing "No documents"

### TC-004: Skip empty files
**Maps to:** AC-001  
**Setup:** Create temp dir with one empty `.txt` and one with content  
**Action:** Call `load_documents(tmp_dir)`  
**Assert:** Returns only the non-empty file

### TC-005: Chunk documents into multiple pieces
**Maps to:** AC-001  
**Setup:** Create doc with 500+ words  
**Action:** Call `chunk_documents(docs, chunk_size=100, chunk_overlap=20)`  
**Assert:**
- Returns more than 1 chunk
- Each chunk has `text`, `source`, `page`, `chunk_id`
- `chunk_id` values are sequential (0, 1, 2, ...)

### TC-006: Small document produces single chunk
**Maps to:** AC-001  
**Setup:** Create doc with a few words  
**Action:** Call `chunk_documents(docs, chunk_size=1000, chunk_overlap=0)`  
**Assert:** Returns exactly 1 chunk

### TC-007: Build FAISS index from embeddings
**Maps to:** AC-001  
**Setup:** Create random numpy array (10, 1024) float32  
**Action:** Call `build_faiss_index(embeddings)`  
**Assert:**
- `index.ntotal == 10`
- `index.d == 1024`

### TC-008: FAISS index search returns correct nearest neighbor
**Maps to:** AC-001  
**Setup:** Build index with 10 normalized vectors  
**Action:** Search for vector[0] with top_k=3  
**Assert:** First result index is 0 (self-match)

---

## 2. Retriever Tests (`tests/test_retriever.py`)

### TC-009: Search returns top-K results
**Maps to:** AC-002  
**Setup:** Create `ITRetriever` with mock FAISS index (5 vectors) and mock Bedrock embeddings  
**Action:** Call `retriever.search("password reset", top_k=3)`  
**Assert:**
- Returns exactly 3 results
- Each result has `text`, `source`, `score`

### TC-010: Results include similarity scores
**Maps to:** AC-002  
**Action:** Call `retriever.search("any query")`  
**Assert:** All scores are floats

### TC-011: Format context produces readable string with sources
**Maps to:** AC-004  
**Setup:** Create result list with 2 items  
**Action:** Call `retriever.format_context(results)`  
**Assert:**
- Contains "[Source 1:" and "[Source 2:"
- Contains text from both results

### TC-012: Format context handles empty results
**Maps to:** AC-005  
**Action:** Call `retriever.format_context([])`  
**Assert:** Contains "No relevant" or similar message

### TC-013: document_count property
**Maps to:** AC-008  
**Assert:** Returns expected count from metadata

### TC-014: vector_count property
**Maps to:** AC-008  
**Assert:** Returns `index.ntotal`

---

## 3. Agent Tests (`tests/test_agent.py`)

### TC-015: Agent calls retrieval tool and returns answer
**Maps to:** AC-003  
**Setup:** Mock the retriever to return fixed chunks about password reset  
**Action:** Call `ask("How do I reset my password?")`  
**Assert:**
- Response has `answer` key with non-empty string
- Response has `sources` key with list

### TC-016: Agent includes source citations
**Maps to:** AC-004  
**Setup:** Mock retriever returning chunks from `password_reset.txt`  
**Action:** Call `ask("How do I reset my password?")`  
**Assert:** Sources list contains entry with `document` = "password_reset.txt"

### TC-017: Agent flags escalation for out-of-scope questions
**Maps to:** AC-005  
**Setup:** Mock retriever returning low-relevance or empty results  
**Action:** Call `ask("My account has been hacked and I see suspicious activity")`  
**Assert:**
- `escalation` is `True`
- `escalation_reason` is not None/empty

### TC-018: Response schema has all required fields
**Maps to:** AC-003, AC-005  
**Action:** Call `ask("any question")`  
**Assert:** Response dict has keys: `answer`, `sources`, `escalation`, `escalation_reason`

---

## 4. API Tests (`tests/test_api.py`)

### TC-019: POST /ask returns 200 with valid question
**Maps to:** AC-006  
**Setup:** Mock the `ask()` function  
**Action:** POST `/ask` with `{"question": "How do I connect to VPN?"}`  
**Assert:**
- Status 200
- Response has `answer`, `sources`, `escalation`, `escalation_reason`

### TC-020: POST /ask returns 422 for missing question
**Maps to:** AC-007  
**Action:** POST `/ask` with `{}`  
**Assert:** Status 422

### TC-021: POST /ask returns 422 for too-short question
**Maps to:** AC-007  
**Action:** POST `/ask` with `{"question": "Hi"}`  
**Assert:** Status 422

### TC-022: POST /ask returns escalation response
**Maps to:** AC-005, AC-006  
**Setup:** Mock `ask()` to return escalation response  
**Action:** POST `/ask` with `{"question": "My account is locked"}`  
**Assert:**
- Status 200
- `escalation` is `true`
- `escalation_reason` is present

### TC-023: GET /health returns 200 with stats
**Maps to:** AC-008  
**Setup:** Mock retriever  
**Action:** GET `/health`  
**Assert:**
- Status 200
- Has `status`, `documents_indexed`, `vector_count`
- `status` is "healthy"

### TC-024: GET /health returns degraded when no index
**Maps to:** AC-008  
**Setup:** Mock retriever to raise exception  
**Action:** GET `/health`  
**Assert:** `status` is "degraded"

---

## 5. Integration Tests (optional, require AWS credentials)

### TC-025: Full ingestion of sample docs
**Maps to:** AC-009  
**Prereq:** AWS credentials, Bedrock access  
**Action:** Run `python -m it_support_agent.main ingest`  
**Assert:**
- No errors
- `data/vector_store/index.faiss` exists
- `data/vector_store/metadata.json` exists
- Index has vectors > 0

### TC-026: End-to-end question answering
**Maps to:** AC-003, AC-006  
**Prereq:** Ingested index, AWS credentials  
**Action:** POST `/ask` with real question  
**Assert:** Returns meaningful answer with sources

---

## Coverage Requirements

| Module | Target |
|--------|--------|
| `ingestion.py` | 90%+ |
| `retriever.py` | 85%+ |
| `agent.py` | 75%+ (mocked LLM calls) |
| `api.py` | 90%+ |
| `config.py` | 100% (simple constants) |
| **Overall** | **80%+** |
