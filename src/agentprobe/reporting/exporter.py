import csv
import json
import sqlite3
from typing import Any


class ReportExporter:
    def __init__(self, db_path: str = "agentprobe.db") -> None:
        self.db_path = db_path

    def generate_summary(self) -> dict[str, Any]:
        """Calculates high-level metrics from all traces in the database."""
        summary = {
            "total_runs": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "total_tool_calls": 0,
            "average_cost_per_run": 0.0
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            try:
                rows = conn.execute("SELECT * FROM traces").fetchall()
            except sqlite3.OperationalError:
                return summary # Table doesn't exist yet
                
            summary["total_runs"] = len(rows)
            
            for row in rows:
                summary["total_cost"] += row["total_cost"]
                summary["total_tokens"] += row["total_tokens"]
                
                steps = json.loads(row["steps_json"])
                for step in steps:
                    summary["total_tool_calls"] += len(step.get("tool_calls", []))
                    
        if summary["total_runs"] > 0:
            summary["average_cost_per_run"] = summary["total_cost"] / summary["total_runs"]
            
        return summary

    def export_to_csv(self, output_path: str) -> None:
        """Exports all traces to a flat CSV file for external dashboarding."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute("SELECT run_id, task_id, total_cost, total_tokens, final_answer FROM traces").fetchall()
            except sqlite3.OperationalError:
                rows = []

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["run_id", "task_id", "total_cost", "total_tokens", "final_answer"])
            for row in rows:
                writer.writerow([row["run_id"], row["task_id"], round(row["total_cost"], 5), row["total_tokens"], row["final_answer"]])

    def export_to_markdown(self, output_path: str) -> None:
        """Generates a human-readable markdown report of the experiment campaign."""
        summary = self.generate_summary()
        
        md = [
            "# AgentProbe Campaign Report",
            "",
            "## Aggregate Metrics",
            f"- **Total Runs:** {summary['total_runs']}",
            f"- **Total Cost:** ${summary['total_cost']:.5f}",
            f"- **Average Cost per Run:** ${summary['average_cost_per_run']:.5f}",
            f"- **Total Tokens Consumed:** {summary['total_tokens']}",
            f"- **Total Tool Calls Executed:** {summary['total_tool_calls']}",
            ""
        ]
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))