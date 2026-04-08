"""Tests for the API layer (TC-019 to TC-024)."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture()
def mock_ask_normal() -> dict:
    """Standard non-escalation response."""
    return {
        "answer": "To connect to VPN, open Cisco AnyConnect and enter vpn.acmecorp.com.",
        "sources": [
            {"document": "vpn_guide.txt", "section": "Connecting", "relevance_score": 0.91}
        ],
        "escalation": False,
        "escalation_reason": None,
    }


@pytest.fixture()
def mock_ask_escalation() -> dict:
    """Escalation response."""
    return {
        "answer": "Please contact the IT Help Desk for account lockout issues.",
        "sources": [],
        "escalation": True,
        "escalation_reason": "Account lockout requires manual intervention by IT admin",
    }


# --- TC-019: POST /ask returns 200 with valid question ---
@patch("it_support_agent.api.ask")
@patch("it_support_agent.api._retriever")
async def test_post_ask_returns_200(
    mock_retriever: MagicMock,
    mock_ask_fn: MagicMock,
    mock_ask_normal: dict,
) -> None:
    """TC-019: POST /ask returns 200 with answer and all required fields."""
    mock_ask_fn.return_value = mock_ask_normal
    mock_retriever.document_count = 5
    mock_retriever.vector_count = 50

    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ask", json={"question": "How do I connect to VPN?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "escalation" in data
    assert "escalation_reason" in data
    assert data["escalation"] is False


# --- TC-020: POST /ask returns 422 for missing question ---
@patch("it_support_agent.api._retriever")
async def test_post_ask_missing_question_returns_422(mock_retriever: MagicMock) -> None:
    """TC-020: POST /ask with empty body returns 422."""
    mock_retriever.document_count = 5
    mock_retriever.vector_count = 50

    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ask", json={})

    assert resp.status_code == 422


# --- TC-021: POST /ask returns 422 for too-short question ---
@patch("it_support_agent.api._retriever")
async def test_post_ask_short_question_returns_422(mock_retriever: MagicMock) -> None:
    """TC-021: POST /ask with very short question returns 422."""
    mock_retriever.document_count = 5
    mock_retriever.vector_count = 50

    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ask", json={"question": "Hi"})

    assert resp.status_code == 422


# --- TC-022: POST /ask returns escalation response ---
@patch("it_support_agent.api.ask")
@patch("it_support_agent.api._retriever")
async def test_post_ask_escalation(
    mock_retriever: MagicMock,
    mock_ask_fn: MagicMock,
    mock_ask_escalation: dict,
) -> None:
    """TC-022: POST /ask returns escalation fields when needed."""
    mock_ask_fn.return_value = mock_ask_escalation
    mock_retriever.document_count = 5
    mock_retriever.vector_count = 50

    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ask", json={"question": "My account is locked out"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["escalation"] is True
    assert data["escalation_reason"] is not None


# --- TC-023: GET /health returns 200 with stats ---
@patch("it_support_agent.api._retriever")
async def test_get_health_returns_stats(mock_retriever: MagicMock) -> None:
    """TC-023: GET /health returns status, documents_indexed, vector_count."""
    mock_retriever.document_count = 5
    mock_retriever.vector_count = 50

    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "documents_indexed" in data
    assert "vector_count" in data


# --- TC-024: GET /health returns degraded when no index ---
@patch("it_support_agent.api._retriever", None)
async def test_get_health_degraded_when_no_index() -> None:
    """TC-024: GET /health returns degraded status when retriever is unavailable."""
    from it_support_agent.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
