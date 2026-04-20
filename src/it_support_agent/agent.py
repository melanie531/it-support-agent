"""IT Support Agent using Strands SDK with RAG retrieval tool."""

import json
import logging
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

from it_support_agent.config import (
    LLM_MAX_TOKENS,
    LLM_MODEL_ID,
    LLM_TEMPERATURE,
    SYSTEM_PROMPT,
)
from it_support_agent.retriever import ITRetriever

logger = logging.getLogger(__name__)

# Module-level retriever — initialized lazily
_retriever: ITRetriever | None = None


def _get_retriever() -> ITRetriever:
    """Get or initialize the module-level ITRetriever.

    Returns:
        The ITRetriever instance.
    """
    global _retriever  # noqa: PLW0603
    if _retriever is None:
        _retriever = ITRetriever()
    return _retriever


def init_retriever(store_dir: str | None = None) -> None:
    """Explicitly initialize the retriever (e.g., during app startup).

    Args:
        store_dir: Optional path to the vector store directory.
    """
    global _retriever  # noqa: PLW0603
    if store_dir:
        _retriever = ITRetriever(store_dir=store_dir)
    else:
        _retriever = ITRetriever()


@tool
def retrieve_it_context(query: str) -> str:
    """Search the IT knowledge base for information relevant to the query.

    Args:
        query: The search query describing the IT issue or question.

    Returns:
        Formatted context string with relevant knowledge base excerpts and source citations.
    """
    retriever = _get_retriever()
    results = retriever.search(query)
    context = retriever.format_context(results)
    logger.info("Retrieved %d results for query: %s", len(results), query)
    return context


def create_agent() -> Agent:
    """Create and configure the IT Support Agent.

    Returns:
        Configured Strands Agent instance.
    """
    model = BedrockModel(
        model_id=LLM_MODEL_ID,
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
    )

    return Agent(
        model=model,
        tools=[retrieve_it_context],
        system_prompt=SYSTEM_PROMPT + _response_format_instruction(),
    )


def _response_format_instruction() -> str:
    """Return the instruction appended to the system prompt for structured output."""
    return """

RESPONSE FORMAT:
After using the retrieve_it_context tool and formulating your answer, you MUST respond with
a JSON object (and nothing else) with exactly these fields:
{
  "answer": "<your helpful answer to the employee>",
  "sources": [{"document": "<filename>", "section": "<section name>", "relevance_score": <float>}],
  "escalation": <true or false>,
  "escalation_reason": "<reason string or null>"
}

If escalation is false, set escalation_reason to null.
Always respond with valid JSON only — no extra text before or after."""


def _parse_agent_response(result: Any) -> dict:
    """Parse the agent's response into a structured dict.

    Args:
        result: The raw agent result object.

    Returns:
        Dict with keys: answer, sources, escalation, escalation_reason.
    """
    # Extract text from the agent result
    text = ""
    if hasattr(result, "message") and result.message:
        content = result.message.get("content", [])
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text = block["text"]
                break

    # Try to parse as JSON
    try:
        parsed = json.loads(text)
        return {
            "answer": parsed.get("answer", text),
            "sources": parsed.get("sources", []),
            "escalation": parsed.get("escalation", False),
            "escalation_reason": parsed.get("escalation_reason"),
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse agent response as JSON, returning raw text")
        return {
            "answer": text or str(result),
            "sources": [],
            "escalation": False,
            "escalation_reason": None,
        }


def ask(question: str) -> dict:
    """Ask the IT Support Agent a question.

    Args:
        question: The IT support question from the employee.

    Returns:
        Dict with keys: answer, sources, escalation, escalation_reason.
    """
    agent = create_agent()
    result = agent(question)
    response = _parse_agent_response(result)
    logger.info(
        "Question: %s | Escalation: %s",
        question[:80],
        response["escalation"],
    )
    return response
