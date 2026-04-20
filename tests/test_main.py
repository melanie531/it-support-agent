"""Tests for the CLI entry point."""

from unittest.mock import MagicMock, patch

import pytest


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI --help exits with usage information."""
    from it_support_agent.main import main

    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["it_support_agent", "--help"]):
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "ingest" in captured.out
    assert "serve" in captured.out
    assert "ask" in captured.out


def test_cli_no_command() -> None:
    """CLI with no command exits with error."""
    from it_support_agent.main import main

    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["it_support_agent"]):
            main()
    assert exc_info.value.code != 0


@patch("it_support_agent.ingestion.run_ingestion")
def test_cmd_ingest(mock_run: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """ingest command calls run_ingestion and prints stats."""
    mock_run.return_value = {"documents": 5, "chunks": 30, "vectors": 30}

    from it_support_agent.main import main

    with patch("sys.argv", ["it_support_agent", "ingest"]):
        main()

    mock_run.assert_called_once()
    captured = capsys.readouterr()
    assert "Documents: 5" in captured.out
    assert "Chunks:    30" in captured.out


@patch("it_support_agent.ingestion.run_ingestion")
def test_cmd_ingest_custom_dirs(mock_run: MagicMock) -> None:
    """ingest command respects --docs-dir and --store-dir."""
    mock_run.return_value = {"documents": 1, "chunks": 5, "vectors": 5}

    from it_support_agent.main import main

    with patch("sys.argv", [
        "it_support_agent", "ingest",
        "--docs-dir", "/tmp/docs",
        "--store-dir", "/tmp/store",
    ]):
        main()

    mock_run.assert_called_once_with("/tmp/docs", "/tmp/store")


@patch("it_support_agent.agent.ask")
def test_cmd_ask(mock_ask: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """ask command calls ask() and prints the answer."""
    mock_ask.return_value = {
        "answer": "Reset your password at sso.acmecorp.com.",
        "sources": [{"document": "password_reset.txt", "section": "Self-Service", "relevance_score": 0.9}],
        "escalation": False,
        "escalation_reason": None,
    }

    from it_support_agent.main import main

    with patch("sys.argv", ["it_support_agent", "ask", "How do I reset my password?"]):
        main()

    mock_ask.assert_called_once_with("How do I reset my password?")
    captured = capsys.readouterr()
    assert "Reset your password" in captured.out
    assert "password_reset.txt" in captured.out


@patch("it_support_agent.agent.ask")
def test_cmd_ask_escalation(mock_ask: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """ask command shows escalation notice when flagged."""
    mock_ask.return_value = {
        "answer": "Please contact IT Help Desk.",
        "sources": [],
        "escalation": True,
        "escalation_reason": "Account lockout requires admin",
    }

    from it_support_agent.main import main

    with patch("sys.argv", ["it_support_agent", "ask", "My account is locked"]):
        main()

    captured = capsys.readouterr()
    assert "ESCALATION" in captured.out
    assert "Account lockout" in captured.out


@patch("uvicorn.run")
def test_cmd_serve(mock_uvicorn_run: MagicMock) -> None:
    """serve command calls uvicorn.run."""
    from it_support_agent.main import main

    with patch("sys.argv", ["it_support_agent", "serve"]):
        main()

    mock_uvicorn_run.assert_called_once()


@patch("uvicorn.run")
def test_cmd_serve_custom_port(mock_uvicorn_run: MagicMock) -> None:
    """serve command respects --port flag."""
    from it_support_agent.main import main

    with patch("sys.argv", ["it_support_agent", "serve", "--port", "9000"]):
        main()

    mock_uvicorn_run.assert_called_once()
    call_kwargs = mock_uvicorn_run.call_args
    assert call_kwargs[1].get("port") == 9000 or call_kwargs[0][2] == 9000 or 9000 in str(call_kwargs)
