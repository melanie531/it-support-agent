"""FastAPI application for the IT Support Agent."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel, Field

from it_support_agent.agent import ask, init_retriever
from it_support_agent.retriever import ITRetriever

logger = logging.getLogger(__name__)

# Module-level retriever reference for health checks
_retriever: ITRetriever | None = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize the retriever on startup."""
    global _retriever  # noqa: PLW0603
    try:
        init_retriever()
        _retriever = ITRetriever()
        logger.info("IT Support Agent API started, retriever loaded.")
    except FileNotFoundError:
        logger.warning("Vector store not found — run 'ingest' first. Health will report degraded.")
        _retriever = None
    yield


app = FastAPI(
    title="IT Support Agent",
    description="RAG-powered IT support agent for Acme Corporation",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Request / Response models ---

class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""

    question: str = Field(..., min_length=5, description="The IT support question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")


class SourceItem(BaseModel):
    """A source citation in the response."""

    document: str
    section: str
    relevance_score: float


class AskResponse(BaseModel):
    """Response body for the /ask endpoint."""

    answer: str
    sources: list[SourceItem]
    escalation: bool
    escalation_reason: str | None


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: str
    documents_indexed: int
    vector_count: int


# --- Endpoints ---

@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest) -> AskResponse:
    """Submit an IT support question and get an answer with sources.

    Args:
        request: The ask request containing the question.

    Returns:
        Answer with source citations and escalation status.
    """
    result = ask(request.question)
    sources = [
        SourceItem(
            document=s.get("document", "unknown"),
            section=s.get("section", "unknown"),
            relevance_score=s.get("relevance_score", 0.0),
        )
        for s in result.get("sources", [])
    ]
    return AskResponse(
        answer=result["answer"],
        sources=sources,
        escalation=result["escalation"],
        escalation_reason=result.get("escalation_reason"),
    )


@app.get("/health", response_model=HealthResponse)
async def health_endpoint() -> HealthResponse:
    """Check service health and index statistics.

    Returns:
        Health status with document and vector counts.
    """
    if _retriever is None:
        return HealthResponse(status="degraded", documents_indexed=0, vector_count=0)

    try:
        return HealthResponse(
            status="healthy",
            documents_indexed=_retriever.document_count,
            vector_count=_retriever.vector_count,
        )
    except Exception:
        logger.exception("Health check failed")
        return HealthResponse(status="degraded", documents_indexed=0, vector_count=0)
