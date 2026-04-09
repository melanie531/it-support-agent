"""Tests for the ingestion pipeline (TC-001 to TC-008)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest


# --- TC-001: Load TXT files from directory ---
def test_load_documents_returns_all_txt_files(tmp_path: Path) -> None:
    """TC-001: load_documents returns list with correct structure for each file."""
    (tmp_path / "doc1.txt").write_text("Hello world")
    (tmp_path / "doc2.txt").write_text("Second document")

    from it_support_agent.ingestion import load_documents

    docs = load_documents(str(tmp_path))

    assert len(docs) == 2
    for doc in docs:
        assert "text" in doc
        assert "source" in doc
        assert "page" in doc
    sources = {d["source"] for d in docs}
    assert sources == {"doc1.txt", "doc2.txt"}


# --- TC-002: Raise FileNotFoundError for missing directory ---
def test_load_documents_missing_dir_raises() -> None:
    """TC-002: load_documents raises FileNotFoundError for nonexistent path."""
    from it_support_agent.ingestion import load_documents

    with pytest.raises(FileNotFoundError):
        load_documents("/nonexistent/path")


# --- TC-003: Raise ValueError for empty directory ---
def test_load_documents_empty_dir_raises(tmp_path: Path) -> None:
    """TC-003: load_documents raises ValueError for directory with no docs."""
    from it_support_agent.ingestion import load_documents

    with pytest.raises(ValueError, match="No documents"):
        load_documents(str(tmp_path))


# --- TC-004: Skip empty files ---
def test_load_documents_skips_empty_files(tmp_path: Path) -> None:
    """TC-004: load_documents skips empty .txt files."""
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "content.txt").write_text("Has content")

    from it_support_agent.ingestion import load_documents

    docs = load_documents(str(tmp_path))

    assert len(docs) == 1
    assert docs[0]["source"] == "content.txt"


# --- TC-005: Chunk documents into multiple pieces ---
def test_chunk_documents_splits_long_text() -> None:
    """TC-005: chunk_documents produces multiple chunks for long text."""
    from it_support_agent.ingestion import chunk_documents

    long_text = "word " * 200  # ~1000 chars
    docs = [{"text": long_text, "source": "test.txt", "page": 1}]

    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk["text"]
        assert chunk["source"] == "test.txt"
        assert chunk["page"] == 1
        assert chunk["chunk_id"] == i


# --- TC-006: Small document produces single chunk ---
def test_chunk_documents_small_doc_single_chunk() -> None:
    """TC-006: Small document produces exactly 1 chunk."""
    from it_support_agent.ingestion import chunk_documents

    docs = [{"text": "Short text.", "source": "small.txt", "page": 1}]

    chunks = chunk_documents(docs, chunk_size=1000, chunk_overlap=0)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Short text."


# --- TC-007: Build FAISS index from embeddings ---
def test_build_faiss_index_dimensions() -> None:
    """TC-007: build_faiss_index creates index with correct ntotal and dimension."""
    from it_support_agent.ingestion import build_faiss_index

    embeddings = np.random.randn(10, 1024).astype(np.float32)

    index = build_faiss_index(embeddings)

    assert index.ntotal == 10
    assert index.d == 1024


# --- TC-008: FAISS index search returns correct nearest neighbor ---
def test_faiss_index_search_self_match() -> None:
    """TC-008: Searching for a vector returns itself as the top result."""
    from it_support_agent.ingestion import build_faiss_index

    rng = np.random.default_rng(42)
    vectors = rng.standard_normal((10, 1024)).astype(np.float32)
    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms

    index = build_faiss_index(vectors)

    query = vectors[0:1]
    scores, indices = index.search(query, 3)
    assert indices[0][0] == 0


# --- TC: embed_chunks calls Bedrock and returns correct shape ---
@patch("it_support_agent.ingestion.boto3")
def test_embed_chunks_returns_numpy_array(mock_boto3: MagicMock) -> None:
    """embed_chunks returns numpy array of shape (n_chunks, 1024)."""
    from it_support_agent.ingestion import embed_chunks

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.invoke_model.return_value = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {"embedding": [0.1] * 1024}
                ).encode()
            )
        )
    }

    chunks = [
        {"text": "chunk one", "source": "a.txt", "page": 1, "chunk_id": 0},
        {"text": "chunk two", "source": "a.txt", "page": 1, "chunk_id": 1},
    ]

    result = embed_chunks(chunks, "amazon.titan-embed-text-v2:0")

    assert isinstance(result, np.ndarray)
    assert result.shape == (2, 1024)


# --- TC: save_index writes files to disk ---
def test_save_index_creates_files(tmp_path: Path) -> None:
    """save_index writes index.faiss and metadata.json."""
    from it_support_agent.ingestion import save_index

    dim = 1024
    index = faiss.IndexFlatIP(dim)
    vectors = np.random.randn(3, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    metadata = [{"text": "a", "source": "a.txt", "page": 1, "chunk_id": 0}]

    save_index(index, metadata, str(tmp_path))

    assert (tmp_path / "index.faiss").exists()
    assert (tmp_path / "metadata.json").exists()

    with open(tmp_path / "metadata.json") as f:
        loaded = json.load(f)
    assert len(loaded) == 1


# --- TC: run_ingestion orchestrates full pipeline ---
@patch("it_support_agent.ingestion.embed_chunks")
def test_run_ingestion_returns_stats(mock_embed: MagicMock, tmp_path: Path) -> None:
    """run_ingestion returns stats dict with documents, chunks, vectors."""
    from it_support_agent.ingestion import run_ingestion

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "test.txt").write_text("word " * 100)

    store_dir = tmp_path / "store"
    store_dir.mkdir()

    mock_embed.return_value = np.random.randn(5, 1024).astype(np.float32)

    stats = run_ingestion(str(docs_dir), str(store_dir))

    assert "documents" in stats
    assert "chunks" in stats
    assert "vectors" in stats
    assert stats["documents"] >= 1
    assert stats["chunks"] >= 1
    assert stats["vectors"] >= 1
