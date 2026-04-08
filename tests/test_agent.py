"""Tests for the agent module (TC-015 to TC-018)."""

from unittest.mock import MagicMock, patch

import pytest


MOCK_RETRIEVER_RESULTS = [
    {
        "text": "To reset your password, go to https://sso.acmecorp.com and click 'Forgot Password'.",
        "source": "password_reset.txt",
        "page": 1,
        "chunk_id": 0,
        "score": 0.92,
    },
    {
        "text": "Password requirements: minimum 12 characters, one uppercase, one number.",
        "source": "password_reset.txt",
        "page": 1,
        "chunk_id": 1,
        "score": 0.85,
    },
]

MOCK_EMPTY_RESULTS: list[dict] = []


@pytest.fixture()
def mock_retriever() -> MagicMock:
    """Create a mock ITRetriever that returns password reset chunks."""
    retriever = MagicMock()
    retriever.search.return_value = MOCK_RETRIEVER_RESULTS
    retriever.format_context.return_value = (
        "[Source 1: password_reset.txt]\n"
        "To reset your password, go to https://sso.acmecorp.com and click 'Forgot Password'.\n\n"
        "[Source 2: password_reset.txt]\n"
        "Password requirements: minimum 12 characters, one uppercase, one number."
    )
    return retriever


@pytest.fixture()
def mock_empty_retriever() -> MagicMock:
    """Create a mock ITRetriever that returns empty results."""
    retriever = MagicMock()
    retriever.search.return_value = MOCK_EMPTY_RESULTS
    retriever.format_context.return_value = "No relevant information found in the IT knowledge base."
    return retriever


# --- TC-015: Agent calls retrieval tool and returns answer ---
@patch("it_support_agent.agent._retriever")
@patch("it_support_agent.agent.Agent")
def test_ask_returns_answer_with_sources(
    mock_agent_cls: MagicMock,
    mock_retriever_global: MagicMock,
    mock_retriever: MagicMock,
) -> None:
    """TC-015: ask() returns dict with answer and sources."""
    from it_support_agent.agent import ask

    mock_retriever_global.search = mock_retriever.search
    mock_retriever_global.format_context = mock_retriever.format_context

    mock_agent_instance = MagicMock()
    mock_agent_cls.return_value = mock_agent_instance

    # Simulate agent response
    mock_result = MagicMock()
    mock_result.message = {
        "content": [
            {
                "text": '{"answer": "To reset your password, visit sso.acmecorp.com.", '
                '"sources": [{"document": "password_reset.txt", "section": "Self-Service Reset", "relevance_score": 0.92}], '
                '"escalation": false, "escalation_reason": null}'
            }
        ]
    }
    mock_agent_instance.return_value = mock_result

    result = ask("How do I reset my password?")

    assert "answer" in result
    assert result["answer"]
    assert "sources" in result


# --- TC-016: Agent includes source citations ---
@patch("it_support_agent.agent._retriever")
@patch("it_support_agent.agent.Agent")
def test_ask_includes_source_citations(
    mock_agent_cls: MagicMock,
    mock_retriever_global: MagicMock,
    mock_retriever: MagicMock,
) -> None:
    """TC-016: Sources list contains entry with document name."""
    from it_support_agent.agent import ask

    mock_retriever_global.search = mock_retriever.search
    mock_retriever_global.format_context = mock_retriever.format_context

    mock_agent_instance = MagicMock()
    mock_agent_cls.return_value = mock_agent_instance

    mock_result = MagicMock()
    mock_result.message = {
        "content": [
            {
                "text": '{"answer": "Visit sso.acmecorp.com to reset.", '
                '"sources": [{"document": "password_reset.txt", "section": "Self-Service Reset", "relevance_score": 0.92}], '
                '"escalation": false, "escalation_reason": null}'
            }
        ]
    }
    mock_agent_instance.return_value = mock_result

    result = ask("How do I reset my password?")

    assert len(result["sources"]) > 0
    documents = [s["document"] for s in result["sources"]]
    assert "password_reset.txt" in documents


# --- TC-017: Agent flags escalation for out-of-scope questions ---
@patch("it_support_agent.agent._retriever")
@patch("it_support_agent.agent.Agent")
def test_ask_flags_escalation(
    mock_agent_cls: MagicMock,
    mock_retriever_global: MagicMock,
    mock_empty_retriever: MagicMock,
) -> None:
    """TC-017: ask() returns escalation=True for security incidents."""
    from it_support_agent.agent import ask

    mock_retriever_global.search = mock_empty_retriever.search
    mock_retriever_global.format_context = mock_empty_retriever.format_context

    mock_agent_instance = MagicMock()
    mock_agent_cls.return_value = mock_agent_instance

    mock_result = MagicMock()
    mock_result.message = {
        "content": [
            {
                "text": '{"answer": "Please contact IT Help Desk immediately.", '
                '"sources": [], '
                '"escalation": true, "escalation_reason": "Security incident requires human intervention"}'
            }
        ]
    }
    mock_agent_instance.return_value = mock_result

    result = ask("My account has been hacked and I see suspicious activity")

    assert result["escalation"] is True
    assert result["escalation_reason"] is not None
    assert result["escalation_reason"] != ""


# --- TC-018: Response schema has all required fields ---
@patch("it_support_agent.agent._retriever")
@patch("it_support_agent.agent.Agent")
def test_ask_response_has_all_fields(
    mock_agent_cls: MagicMock,
    mock_retriever_global: MagicMock,
    mock_retriever: MagicMock,
) -> None:
    """TC-018: Response dict has all required keys."""
    from it_support_agent.agent import ask

    mock_retriever_global.search = mock_retriever.search
    mock_retriever_global.format_context = mock_retriever.format_context

    mock_agent_instance = MagicMock()
    mock_agent_cls.return_value = mock_agent_instance

    mock_result = MagicMock()
    mock_result.message = {
        "content": [
            {
                "text": '{"answer": "Here is your answer.", '
                '"sources": [{"document": "doc.txt", "section": "Sec", "relevance_score": 0.5}], '
                '"escalation": false, "escalation_reason": null}'
            }
        ]
    }
    mock_agent_instance.return_value = mock_result

    result = ask("any question")

    required_keys = {"answer", "sources", "escalation", "escalation_reason"}
    assert required_keys.issubset(result.keys())
