import os
import sqlite3
from pathlib import Path

from agentprobe.reporting.exporter import ReportExporter


def test_generate_summary_and_exports(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test_report.db")
    csv_path = str(tmp_path / "report.csv")
    md_path = str(tmp_path / "report.md")
    
    # 1. Seed the database with some dummy traces
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE traces (
                run_id TEXT PRIMARY KEY, system_prompt TEXT, task_id TEXT, task_desc TEXT,
                final_answer TEXT, total_cost REAL, total_tokens INTEGER, steps_json TEXT
            )
        """)
        
        # Insert 2 dummy runs
        steps_json = '[{"step_num": 1, "tool_calls": [{"call_id": "1", "name": "test_tool", "arguments": {}}]}]'
        conn.execute("INSERT INTO traces VALUES ('run1', 'sys', 't1', 'desc1', 'ans1', 0.50, 100, ?)", (steps_json,))
        conn.execute("INSERT INTO traces VALUES ('run2', 'sys', 't2', 'desc2', 'ans2', 1.50, 300, ?)", (steps_json,))
        conn.commit()

    exporter = ReportExporter(db_path)
    
    # 2. Test Summary Math
    summary = exporter.generate_summary()
    assert summary["total_runs"] == 2
    assert summary["total_cost"] == 2.0
    assert summary["total_tokens"] == 400
    assert summary["total_tool_calls"] == 2
    assert summary["average_cost_per_run"] == 1.0
    
    # 3. Test CSV Export
    exporter.export_to_csv(csv_path)
    assert os.path.exists(csv_path)
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 3 # Header + 2 rows
        assert "run1,t1,0.5,100,ans1" in lines[1].strip()
        
    # 4. Test Markdown Export
    exporter.export_to_markdown(md_path)
    assert os.path.exists(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "**Total Runs:** 2" in content
        assert "**Total Cost:** $2.00000" in content