"""IT knowledge base retriever using FAISS vector search."""

import json
import logging
from pathlib import Path

import boto3
import faiss
import numpy as np

from it_support_agent.config import (
    EMBEDDING_MODEL_ID,
    INDEX_FILENAME,
    METADATA_FILENAME,
    TOP_K,
    VECTOR_STORE_DIR,
)

logger = logging.getLogger(__name__)


class ITRetriever:
    """Retrieves relevant IT knowledge base chunks using FAISS similarity search."""

    def __init__(self, store_dir: str = VECTOR_STORE_DIR) -> None:
        """Initialize the retriever by loading the FAISS index and metadata.

        Args:
            store_dir: Path to the vector store directory.

        Raises:
            FileNotFoundError: If index or metadata files are missing.
        """
        store_path = Path(store_dir)

        index_path = store_path / INDEX_FILENAME
        metadata_path = store_path / METADATA_FILENAME

        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {metadata_path}")

        self._index = faiss.read_index(str(index_path))

        with open(metadata_path, encoding="utf-8") as f:
            self._metadata: list[dict] = json.load(f)

        self._bedrock_client = boto3.client("bedrock-runtime")
        logger.info(
            "Loaded retriever: %d vectors, %d metadata entries",
            self._index.ntotal,
            len(self._metadata),
        )

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a query string using Bedrock Titan.

        Args:
            query: The search query text.

        Returns:
            Normalized embedding vector of shape (1, dimension).
        """
        body = json.dumps({"inputText": query})
        response = self._bedrock_client.invoke_model(
            modelId=EMBEDDING_MODEL_ID, body=body
        )
        response_body = json.loads(response["body"].read())
        embedding = np.array([response_body["embedding"]], dtype=np.float32)
        faiss.normalize_L2(embedding)
        return embedding

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Search the knowledge base for chunks relevant to the query.

        Args:
            query: Natural language search query.
            top_k: Number of top results to return.

        Returns:
            List of result dicts with keys: text, source, page, chunk_id, score.
        """
        query_embedding = self._embed_query(query)
        scores, indices = self._index.search(query_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            entry = self._metadata[idx].copy()
            entry["score"] = float(score)
            results.append(entry)

        logger.info("Search for '%s' returned %d results", query, len(results))
        return results

    @staticmethod
    def format_context(results: list[dict]) -> str:
        """Format search results into a context string for the LLM.

        Args:
            results: List of search result dicts.

        Returns:
            Formatted context string with source citations.
        """
        if not results:
            return "No relevant information found in the IT knowledge base."

        parts = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "unknown")
            text = result.get("text", "")
            parts.append(f"[Source {i}: {source}]\n{text}")

        return "\n\n".join(parts)

    @property
    def document_count(self) -> int:
        """Return the number of unique source documents in the index."""
        sources = {entry.get("source") for entry in self._metadata}
        return len(sources)

    @property
    def vector_count(self) -> int:
        """Return the total number of vectors in the FAISS index."""
        return self._index.ntotal
