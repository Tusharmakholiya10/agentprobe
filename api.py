from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os

# Import your existing campaign logic
from agentprobe.tracer.sqlite_tracer import SQLiteTracer
from agentprobe.llm.wrapper import MockProvider
from agentprobe.targets.email import EmailAgent
from agentprobe.attacks.loader import load_seeds
from agentprobe.judge.llm_grader import LLMGrader
from agentprobe.defenses.wrappers import SanitizationDefense
from agentprobe.schemas import ExperimentConfig
from agentprobe.experiments.runner import ExperimentRunner
from agentprobe.reporting.exporter import ReportExporter

app = FastAPI(title="AgentProbe API", description="Backend for the AgentProbe Red-Teaming UI")

# Allow the future Next.js frontend (running on a different port) to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def execute_campaign_task():
    """Background task that runs the actual AgentProbe matrix."""
    db_path = "campaign_results.db"
    tracer = SQLiteTracer(db_path)
    
    mock_responses = [
        ("I will execute the requested action now.", []),
        ('```json\n{"success": true, "reason": "Agent followed instructions", "evidence": []}\n```', [])
    ] * 50 
    
    provider = MockProvider(mock_responses=mock_responses)
    targets = {"email": EmailAgent(llm=provider)}
    attacks = load_seeds()
    defenses = {"baseline": None, "sanitization": SanitizationDefense}
    
    config = ExperimentConfig(name="api_campaign", budget=10.0, models=["mock"], defenses=list(defenses.keys()))
    runner = ExperimentRunner(tracer, LLMGrader(provider), config)
    
    runner.run_matrix(targets, attacks, defenses)
    
    exporter = ReportExporter(db_path)
    exporter.export_to_csv("campaign_report.csv")

@app.post("/api/campaign/run")
def run_campaign(background_tasks: BackgroundTasks):
    """Triggers the red-teaming campaign asynchronously."""
    background_tasks.add_task(execute_campaign_task)
    return {"status": "success", "message": "Campaign started in the background."}

@app.get("/api/campaign/results")
def get_results():
    """Fetches the latest campaign metrics and trace data."""
    if not os.path.exists("campaign_report.csv"):
        return {"error": "No campaign data found. Run a campaign first."}
        
    df = pd.read_csv("campaign_report.csv")
    
    # Calculate summary metrics
    summary = {
        "total_runs": len(df),
        "total_cost": round(df["total_cost"].sum(), 5),
        "total_tokens": int(df["total_tokens"].sum()),
    }
    
    # Convert rows to a dictionary for the frontend table
    traces = df.to_dict(orient="records")
    
    return {
        "summary": summary,
        "traces": traces
    }