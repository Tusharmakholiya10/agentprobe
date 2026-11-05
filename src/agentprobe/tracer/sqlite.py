"""SQLite-backed event trace persistence."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentprobe.schemas import Trace, TraceEvent, TraceEventType, utc_now


def max_log_chars() -> int:
    """Maximum characters stored per logged text field (AGENTPROBE_MAX_LOG_CHARS)."""
    try:
        return int(os.getenv("AGENTPROBE_MAX_LOG_CHARS", "20000"))
    except ValueError:
        return 20000


def truncate_text(text: str, limit: int | None = None) -> str:
    """Truncate text for logging, noting how much was cut."""
    limit = max_log_chars() if limit is None else limit
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


class SQLiteTracer:
    """Append-only trace store with deterministic chronological replay."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with foreign-key enforcement."""
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        """Create trace and event tables if they do not exist."""
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    system_prompt TEXT NOT NULL,
                    user_task TEXT NOT NULL,
                    final_answer TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    total_input_tokens INTEGER NOT NULL DEFAULT 0,
                    total_output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_cost_usd REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'running',
                    status_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_events_run_time
                    ON events(run_id, timestamp);
                """
            )
            self._migrate(connection)

    def _migrate(self, connection: sqlite3.Connection) -> None:
        """Add status columns to databases created before they existed."""
        columns = {row[1] for row in connection.execute("PRAGMA table_info(runs)")}
        if "status" not in columns:
            connection.execute(
                "ALTER TABLE runs ADD COLUMN status TEXT NOT NULL DEFAULT 'running'"
            )
            connection.execute(
                "UPDATE runs SET status = 'completed' WHERE finished_at IS NOT NULL"
            )
        if "status_reason" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN status_reason TEXT")

    def start_run(
        self,
        system_prompt: str,
        user_task: str,
        run_id: str | None = None,
    ) -> str:
        """Create a run and its initial prompt/task events."""
        trace = Trace(
            run_id=run_id or str(uuid4()),
            system_prompt=system_prompt,
            user_task=user_task,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs
                (run_id, system_prompt, user_task, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    trace.run_id,
                    system_prompt,
                    user_task,
                    trace.started_at.isoformat(),
                ),
            )

        self.add_event(
            trace.run_id,
            TraceEventType.SYSTEM_PROMPT,
            {"content": system_prompt},
        )

        self.add_event(
            trace.run_id,
            TraceEventType.USER_TASK,
            {"content": user_task},
        )

        return trace.run_id

    def add_event(
        self,
        run_id: str,
        event_type: TraceEventType,
        payload: dict[str, Any],
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        estimated_cost_usd: float = 0.0,
    ) -> TraceEvent:
        """Persist a trace event and update run accounting."""
        event = TraceEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost_usd,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events
                (
                    id,
                    run_id,
                    event_type,
                    payload_json,
                    timestamp,
                    input_tokens,
                    output_tokens,
                    latency_ms,
                    estimated_cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    run_id,
                    event.event_type.value,
                    json.dumps(payload, default=str),
                    event.timestamp.isoformat(),
                    input_tokens,
                    output_tokens,
                    latency_ms,
                    estimated_cost_usd,
                ),
            )

            connection.execute(
                """
                UPDATE runs
                SET total_input_tokens = total_input_tokens + ?,
                    total_output_tokens = total_output_tokens + ?,
                    total_cost_usd = total_cost_usd + ?
                WHERE run_id = ?
                """,
                (
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    run_id,
                ),
            )

        return event

    def finish_run(self, run_id: str, final_answer: str) -> None:
        """Record the final answer and mark the run complete."""
        self.add_event(
            run_id,
            TraceEventType.FINAL_ANSWER,
            {"content": final_answer},
        )

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET final_answer = ?, finished_at = ?, status = 'completed'
                WHERE run_id = ?
                """,
                (final_answer, utc_now().isoformat(), run_id),
            )

    def abort_run(self, run_id: str, reason: str) -> None:
        """Mark a run aborted so reports can exclude or flag it."""
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = 'aborted', status_reason = ?, finished_at = ?
                WHERE run_id = ?
                """,
                (truncate_text(reason, 2000), utc_now().isoformat(), run_id),
            )

    def get_run_status(self, run_id: str) -> tuple[str, str | None]:
        """Return (status, reason) for a run."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, status_reason FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Run not found: {run_id}")
        return str(row[0]), row[1]

    def get_trace(self, run_id: str) -> Trace:
        """Load a complete trace, raising KeyError when no run exists."""
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row

            run = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

            if run is None:
                raise KeyError(f"Run not found: {run_id}")

            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE run_id = ?
                ORDER BY timestamp, rowid
                """,
                (run_id,),
            ).fetchall()

        events = [
            TraceEvent(
                id=row["id"],
                run_id=row["run_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                timestamp=row["timestamp"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                latency_ms=row["latency_ms"],
                estimated_cost_usd=row["estimated_cost_usd"],
            )
            for row in rows
        ]

        return Trace(
            run_id=run["run_id"],
            system_prompt=run["system_prompt"],
            user_task=run["user_task"],
            events=events,
            final_answer=run["final_answer"],
            started_at=run["started_at"],
            finished_at=run["finished_at"],
            total_input_tokens=run["total_input_tokens"],
            total_output_tokens=run["total_output_tokens"],
            total_cost_usd=run["total_cost_usd"],
        )

    def latest_run_id(self) -> str | None:
        """Return the most recently started run ID."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()

        return str(row[0]) if row else None