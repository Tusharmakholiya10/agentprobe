import json
import sqlite3

from agentprobe.schemas import Trace


class SQLiteTracer:
    def __init__(self, db_path: str = "agentprobe.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    run_id TEXT PRIMARY KEY,
                    system_prompt TEXT,
                    task_id TEXT,
                    task_desc TEXT,
                    final_answer TEXT,
                    total_cost REAL,
                    total_tokens INTEGER,
                    steps_json TEXT
                )
            """)
            conn.commit()

    def save_trace(self, trace: Trace):
        steps_json = json.dumps([step.model_dump(mode="json") for step in trace.steps])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO traces 
                (run_id, system_prompt, task_id, task_desc, final_answer, total_cost, total_tokens, steps_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trace.run_id,
                    trace.system_prompt,
                    trace.task.id,
                    trace.task.description,
                    trace.final_answer,
                    trace.total_cost,
                    trace.total_tokens,
                    steps_json,
                ),
            )
            conn.commit()

    def get_trace(self, run_id: str) -> Trace:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM traces WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Run {run_id} not found")

            from agentprobe.schemas import Task, TraceStep

            task = Task(id=row["task_id"], description=row["task_desc"])
            steps = [TraceStep(**s) for s in json.loads(row["steps_json"])]

            return Trace(
                run_id=row["run_id"],
                system_prompt=row["system_prompt"],
                task=task,
                steps=steps,
                final_answer=row["final_answer"],
                total_cost=row["total_cost"],
                total_tokens=row["total_tokens"],
            )
