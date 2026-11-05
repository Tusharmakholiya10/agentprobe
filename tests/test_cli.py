"""CLI smoke test."""

from typer.testing import CliRunner

from agentprobe.cli import app


def test_demo_and_replay(tmp_path, monkeypatch) -> None:
    """Demo creates a trace that the replay command can display."""
    monkeypatch.setenv("AGENTPROBE_DB_PATH", str(tmp_path / "cli.sqlite3"))
    runner = CliRunner()
    created = runner.invoke(app, ["demo"])
    assert created.exit_code == 0, created.output
    replayed = runner.invoke(app, ["replay", "latest"])
    assert replayed.exit_code == 0, replayed.output
    assert "MOCK_RESPONSE" in replayed.output
