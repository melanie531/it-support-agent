"""Document ingestion pipeline: load, chunk, embed, and index IT knowledge base documents."""

import json
import logging
from pathlib import Path

import boto3
import faiss
import numpy as np

from it_support_agent.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_ID,
    INDEX_FILENAME,
    METADATA_FILENAME,
)

logger = logging.getLogger(__name__)


def load_documents(dir_path: str) -> list[dict]:
    """Load all .txt files from a directory.

    Args:
        dir_path: Path to directory containing .txt documents.

    Returns:
        List of dicts with keys: text, source, page.

    Raises:
        FileNotFoundError: If directory does not exist.
        ValueError: If no documents are found.
    """
    directory = Path(dir_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    docs = []
    for txt_file in sorted(directory.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8").strip()
        if not content:
            logger.warning("Skipping empty file: %s", txt_file.name)
            continue
        docs.append({
            "text": content,
            "source": txt_file.name,
            "page": 1,
        })

    if not docs:
        raise ValueError(f"No documents found in {dir_path}")

    logger.info("Loaded %d documents from %s", len(docs), dir_path)
    return docs


def chunk_documents(
    docs: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split documents into overlapping text chunks.

    Args:
        docs: List of document dicts with text, source, page.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of chunk dicts with text, source, page, chunk_id.
    """
    chunks: list[dict] = []
    chunk_id = 0

    for doc in docs:
        text = doc["text"]
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": doc["source"],
                    "page": doc["page"],
                    "chunk_id": chunk_id,
                })
                chunk_id += 1

            if end >= len(text):
                break
            start = end - chunk_overlap

    logger.info("Created %d chunks from %d documents", len(chunks), len(docs))
    return chunks


def embed_chunks(chunks: list[dict], model_id: str = EMBEDDING_MODEL_ID) -> np.ndarray:
    """Generate embeddings for text chunks using Amazon Bedrock Titan.

    Args:
        chunks: List of chunk dicts with text field.
        model_id: Bedrock embedding model ID.

    Returns:
        Numpy array of shape (n_chunks, embedding_dimension).
    """
    client = boto3.client("bedrock-runtime")
    embeddings = []

    for chunk in chunks:
        body = json.dumps({"inputText": chunk["text"]})
        response = client.invoke_model(modelId=model_id, body=body)
        response_body = json.loads(response["body"].read())
        embeddings.append(response_body["embedding"])

    result = np.array(embeddings, dtype=np.float32)
    logger.info("Embedded %d chunks -> shape %s", len(chunks), result.shape)
    return result


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Build a FAISS inner-product index from normalized embeddings.

    Args:
        embeddings: Numpy array of shape (n, dimension).

    Returns:
        FAISS IndexFlatIP with all vectors added.
    """
    embeddings = embeddings.copy()
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    logger.info("Built FAISS index: %d vectors, dimension %d", index.ntotal, dimension)
    return index


def save_index(index: faiss.IndexFlatIP, metadata: list[dict], store_dir: str) -> None:
    """Save FAISS index and metadata to disk.

    Args:
        index: FAISS index to save.
        metadata: List of chunk metadata dicts.
        store_dir: Directory to write files to.
    """
    store_path = Path(store_dir)
    store_path.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(store_path / INDEX_FILENAME))

    with open(store_path / METADATA_FILENAME, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Saved index and metadata to %s", store_dir)


def run_ingestion(docs_dir: str, store_dir: str) -> dict:
    """Run the full ingestion pipeline.

    Args:
        docs_dir: Path to directory containing source documents.
        store_dir: Path to directory for the vector store.

    Returns:
        Stats dict with keys: documents, chunks, vectors.
    """
    docs = load_documents(docs_dir)
    chunks = chunk_documents(docs)
    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)
    save_index(index, chunks, store_dir)

    stats = {
        "documents": len(docs),
        "chunks": len(chunks),
        "vectors": index.ntotal,
    }
    logger.info("Ingestion complete: %s", stats)
    return stats
