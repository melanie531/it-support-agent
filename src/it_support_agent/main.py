"""CLI entry point for the IT Support Agent."""

import argparse
import json
import logging
import sys

from it_support_agent.config import API_HOST, API_PORT, DOCS_DIR, VECTOR_STORE_DIR


def cmd_ingest(args: argparse.Namespace) -> None:
    """Run the ingestion pipeline.

    Args:
        args: Parsed CLI arguments with docs_dir and store_dir.
    """
    from it_support_agent.ingestion import run_ingestion

    docs_dir = args.docs_dir or DOCS_DIR
    store_dir = args.store_dir or VECTOR_STORE_DIR

    print(f"Ingesting documents from: {docs_dir}")
    print(f"Storing index in: {store_dir}")

    stats = run_ingestion(docs_dir, store_dir)

    print(f"Ingestion complete:")
    print(f"  Documents: {stats['documents']}")
    print(f"  Chunks:    {stats['chunks']}")
    print(f"  Vectors:   {stats['vectors']}")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI server.

    Args:
        args: Parsed CLI arguments with host and port.
    """
    import uvicorn

    from it_support_agent.api import app

    host = args.host or API_HOST
    port = args.port or API_PORT

    print(f"Starting IT Support Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def cmd_ask(args: argparse.Namespace) -> None:
    """Ask a one-off question.

    Args:
        args: Parsed CLI arguments with question.
    """
    from it_support_agent.agent import ask

    question = args.question
    print(f"Question: {question}\n")

    result = ask(question)

    print(f"Answer: {result['answer']}\n")

    if result["sources"]:
        print("Sources:")
        for source in result["sources"]:
            doc = source.get("document", "unknown")
            section = source.get("section", "unknown")
            score = source.get("relevance_score", 0.0)
            print(f"  - {doc} / {section} (score: {score:.2f})")

    if result["escalation"]:
        print(f"\n** ESCALATION: {result['escalation_reason']}")


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        prog="it_support_agent",
        description="RAG-powered IT Support Agent",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest IT documents into vector store")
    ingest_parser.add_argument("--docs-dir", help=f"Documents directory (default: {DOCS_DIR})")
    ingest_parser.add_argument("--store-dir", help=f"Vector store directory (default: {VECTOR_STORE_DIR})")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", help=f"Bind host (default: {API_HOST})")
    serve_parser.add_argument("--port", type=int, help=f"Bind port (default: {API_PORT})")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask a question from the command line")
    ask_parser.add_argument("question", help="The IT support question")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    commands = {
        "ingest": cmd_ingest,
        "serve": cmd_serve,
        "ask": cmd_ask,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
