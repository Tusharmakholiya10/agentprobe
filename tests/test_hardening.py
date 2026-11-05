"""Tests for Phase 1 hardening: clean errors, pre-call budget, aborted runs, logging."""

import sqlite3

import pytest
from typer.testing import CliRunner

from agentprobe.cli import app
from agentprobe.llm import create_provider
from agentprobe.llm.base import BudgetExceeded
from agentprobe.schemas import TraceEventType
from agentprobe.tracer import SQLiteTracer
from agentprobe.tracer.sqlite import truncate_text

runner = CliRunner()


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTPROBE_DB_PATH", str(tmp_path / "t.sqlite3"))
    monkeypatch.setenv("AGENTPROBE_PROVIDER", "mock")
    monkeypatch.delenv("AGENTPROBE_DEBUG", raising=False)
    monkeypatch.delenv("AGENTPROBE_MAX_TOKENS", raising=False)
    return tmp_path / "t.sqlite3"


def test_precheck_blocks_before_any_call(monkeypatch):
    monkeypatch.setenv("AGENTPROBE_MAX_TOKENS", "10")
    provider = create_provider()
    with pytest.raises(BudgetExceeded):
        provider.generate("x" * 400, "system")
    assert provider.total_tokens == 0  # nothing was spent


def test_cli_budget_error_is_clean(monkeypatch):
    monkeypatch.setenv("AGENTPROBE_MAX_TOKENS", "10")
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "budget" in result.output.lower()


def test_aborted_run_is_marked(monkeypatch, env):
    monkeypatch.setenv("AGENTPROBE_MAX_TOKENS", "10")
    runner.invoke(app, ["demo"])
    tracer = SQLiteTracer(env)
    run_id = tracer.latest_run_id()
    assert run_id is not None
    status, reason = tracer.get_run_status(run_id)
    assert status == "aborted"
    assert "budget" in (reason or "").lower()


def test_hosted_without_key_is_clean(monkeypatch):
    monkeypatch.setenv("AGENTPROBE_PROVIDER", "hosted")
    monkeypatch.delenv("AGENTPROBE_API_KEY", raising=False)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_llm_call_logs_messages_and_response(env):
    assert runner.invoke(app, ["demo"]).exit_code == 0
    tracer = SQLiteTracer(env)
    run_id = tracer.latest_run_id()
    assert run_id is not None
    trace = tracer.get_trace(run_id)
    call = next(e for e in trace.events if e.event_type == TraceEventType.LLM_CALL)
    assert call.payload["messages"][1]["role"] == "user"
    assert call.payload["response"].startswith("MOCK_RESPONSE")
    assert tracer.get_run_status(trace.run_id)[0] == "completed"


def test_truncate_text():
    assert truncate_text("abc", 10) == "abc"
    assert "truncated 5 chars" in truncate_text("a" * 15, 10)


def test_old_database_is_migrated(tmp_path):
    path = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE runs (run_id TEXT PRIMARY KEY, system_prompt TEXT NOT NULL,
        user_task TEXT NOT NULL, final_answer TEXT, started_at TEXT NOT NULL,
        finished_at TEXT, total_input_tokens INTEGER NOT NULL DEFAULT 0,
        total_output_tokens INTEGER NOT NULL DEFAULT 0,
        total_cost_usd REAL NOT NULL DEFAULT 0)"""
    )
    conn.execute(
        "INSERT INTO runs (run_id, system_prompt, user_task, started_at, finished_at)"
        " VALUES ('old1', 's', 't', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:01+00:00')"
    )
    conn.commit()
    conn.close()
    tracer = SQLiteTracer(path)
    assert tracer.get_run_status("old1") == ("completed", None)