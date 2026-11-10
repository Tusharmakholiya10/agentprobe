import os
from agentprobe.tracer.sqlite_tracer import SQLiteTracer
from agentprobe.llm.wrapper import MockProvider
from agentprobe.targets.email import EmailAgent
from agentprobe.targets.web import WebResearchAgent
from agentprobe.targets.banking import BankingAgent
from agentprobe.attacks.loader import load_seeds
from agentprobe.judge.llm_grader import LLMGrader
from agentprobe.defenses.wrappers import SanitizationDefense
from agentprobe.schemas import ExperimentConfig
from agentprobe.experiments.runner import ExperimentRunner
from agentprobe.reporting.exporter import ReportExporter

def main() -> None:
    print("🚀 Starting AgentProbe End-to-End Campaign...")
    
    # 1. Setup Database & LLM Provider
    db_path = "campaign_results.db"
    tracer = SQLiteTracer(db_path)
    
    # We use MockProvider for instant, free testing. 
    # It returns a mix of agent responses and JSON grader verdicts.
    mock_responses = [
        ("I will execute the requested action now.", []),
        ('```json\n{"success": true, "reason": "Agent followed instructions", "evidence": []}\n```', [])
    ] * 50 # Duplicate to ensure we don't run out of mock responses during the loop
    
    provider = MockProvider(mock_responses=mock_responses)
    
    # 2. Initialize Targets
    targets = {
        "email": EmailAgent(llm=provider),
        "web": WebResearchAgent(llm=provider),
        "banking": BankingAgent(llm=provider)
    }
    
    # 3. Load Attacks
    attacks = load_seeds()
    print(f"📦 Loaded {len(attacks)} attack seeds.")
    if not attacks:
        print("⚠️ No attacks found in src/agentprobe/attacks/seeds/")
        return
        
    # 4. Configure Defenses to Test
    defenses = {
        "baseline": None, # No defense
        "sanitization": SanitizationDefense
    }
    
    # 5. Run the Experiment Matrix
    config = ExperimentConfig(
        name="full_campaign_v1", 
        budget=10.0, 
        models=["mock"], 
        defenses=list(defenses.keys())
    )
    
    grader = LLMGrader(provider)
    runner = ExperimentRunner(tracer, grader, config)
    
    print("⚔️ Running Attack Matrix (Targets x Attacks x Defenses)...")
    runner.run_matrix(targets, attacks, defenses)
    
    # 6. Generate Reports
    print("📊 Generating Reports...")
    exporter = ReportExporter(db_path)
    exporter.export_to_csv("campaign_report.csv")
    exporter.export_to_markdown("campaign_report.md")
    
    print("✅ Campaign Complete! Check campaign_report.md and campaign_report.csv")

if __name__ == "__main__":
    main()