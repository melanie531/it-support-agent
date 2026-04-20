"""Tests for the retriever module (TC-009 to TC-014)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest


@pytest.fixture()
def mock_store(tmp_path: Path) -> Path:
    """Create a mock vector store with a FAISS index and metadata."""
    dim = 1024
    n_vectors = 5

    rng = np.random.default_rng(42)
    vectors = rng.standard_normal((n_vectors, dim)).astype(np.float32)
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(tmp_path / "index.faiss"))

    metadata = [
        {
            "text": f"Content about topic {i}",
            "source": f"doc{i}.txt",
            "page": 1,
            "chunk_id": i,
        }
        for i in range(n_vectors)
    ]
    with open(tmp_path / "metadata.json", "w") as f:
        json.dump(metadata, f)

    return tmp_path


# --- TC-009: Search returns top-K results ---
@patch("it_support_agent.retriever.boto3")
def test_search_returns_top_k(mock_boto3: MagicMock, mock_store: Path) -> None:
    """TC-009: search returns exactly top_k results with correct keys."""
    from it_support_agent.retriever import ITRetriever

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.invoke_model.return_value = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps({"embedding": [0.1] * 1024}).encode()
            )
        )
    }

    retriever = ITRetriever(store_dir=str(mock_store))
    results = retriever.search("password reset", top_k=3)

    assert len(results) == 3
    for r in results:
        assert "text" in r
        assert "source" in r
        assert "score" in r


# --- TC-010: Results include similarity scores ---
@patch("it_support_agent.retriever.boto3")
def test_search_results_have_float_scores(mock_boto3: MagicMock, mock_store: Path) -> None:
    """TC-010: All results have float similarity scores."""
    from it_support_agent.retriever import ITRetriever

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.invoke_model.return_value = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps({"embedding": [0.1] * 1024}).encode()
            )
        )
    }

    retriever = ITRetriever(store_dir=str(mock_store))
    results = retriever.search("any query")

    for r in results:
        assert isinstance(r["score"], float)


# --- TC-011: Format context produces readable string with sources ---
def test_format_context_includes_sources() -> None:
    """TC-011: format_context includes source labels and text."""
    from it_support_agent.retriever import ITRetriever

    results = [
        {"text": "Reset your password via Okta.", "source": "password_reset.txt", "score": 0.9, "page": 1, "chunk_id": 0},
        {"text": "Connect to VPN using AnyConnect.", "source": "vpn_guide.txt", "score": 0.8, "page": 1, "chunk_id": 1},
    ]

    context = ITRetriever.format_context(results)

    assert "[Source 1:" in context
    assert "[Source 2:" in context
    assert "Reset your password" in context
    assert "Connect to VPN" in context


# --- TC-012: Format context handles empty results ---
def test_format_context_empty_results() -> None:
    """TC-012: format_context returns meaningful message for empty results."""
    from it_support_agent.retriever import ITRetriever

    context = ITRetriever.format_context([])

    assert "No relevant" in context


# --- TC-013: document_count property ---
@patch("it_support_agent.retriever.boto3")
def test_document_count(mock_boto3: MagicMock, mock_store: Path) -> None:
    """TC-013: document_count returns count of unique source documents."""
    from it_support_agent.retriever import ITRetriever

    retriever = ITRetriever(store_dir=str(mock_store))

    assert retriever.document_count == 5


# --- TC-014: vector_count property ---
@patch("it_support_agent.retriever.boto3")
def test_vector_count(mock_boto3: MagicMock, mock_store: Path) -> None:
    """TC-014: vector_count returns index.ntotal."""
    from it_support_agent.retriever import ITRetriever

    retriever = ITRetriever(store_dir=str(mock_store))

    assert retriever.vector_count == 5
