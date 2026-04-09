"""Centralized configuration for the IT Support Agent."""

from pathlib import Path

# Model configuration
LLM_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024

# Retrieval configuration
CHUNK_SIZE = 512  # characters per chunk
CHUNK_OVERLAP = 50  # overlap between chunks
TOP_K = 5  # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.3  # minimum score to include a result

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = str(PROJECT_ROOT / "data" / "sample_docs")
VECTOR_STORE_DIR = str(PROJECT_ROOT / "data" / "vector_store")
INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"

# API configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# LLM parameters
LLM_MAX_TOKENS = 1024
LLM_TEMPERATURE = 0.1  # Low temperature for factual accuracy

# System prompt
SYSTEM_PROMPT = """You are an IT Support Agent for Acme Corporation. Your job is to help employees
resolve common IT issues by searching the IT knowledge base.

RULES:
1. ALWAYS use the retrieve_it_context tool to search the knowledge base before
   answering. Never answer from your own knowledge.
2. Provide clear, step-by-step instructions when applicable.
3. Cite your sources — mention which document and section the information comes from.
4. If the knowledge base doesn't contain enough information to answer confidently,
   say so explicitly. Do NOT make up IT procedures.
5. For issues requiring human intervention (account lockouts, hardware failures,
   security incidents, access to restricted systems), recommend the employee
   contact the IT Help Desk at helpdesk@acmecorp.com or ext. 5000.
6. Be friendly and professional. Avoid jargon unless the user seems technical.
7. If the question is not related to IT support, politely redirect the employee
   to the appropriate department.

ESCALATION TRIGGERS (always recommend human help for these):
- Account lockouts or security compromises
- Hardware failures or physical damage
- Network outages affecting multiple users
- Requests for admin/root access
- Data recovery
- Security incidents or suspected breaches"""
