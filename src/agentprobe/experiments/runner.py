import hashlib
from typing import Any
from agentprobe.schemas import Attack, ExperimentConfig
from agentprobe.tracer.sqlite_tracer import SQLiteTracer
from agentprobe.targets.base import BaseTarget
from agentprobe.judge.llm_grader import LLMGrader

class ExperimentRunner:
    def __init__(self, tracer: SQLiteTracer, grader: LLMGrader, config: ExperimentConfig) -> None:
        self.tracer = tracer
        self.grader = grader
        self.config = config
        self.current_spend = 0.0

    def run_matrix(self, targets: dict[str, BaseTarget], attacks: list[Attack], defenses: dict[str, Any]) -> None:
        """Runs the combinatorial matrix: Targets x Attacks x Defenses"""
        for target_name, base_target in targets.items():
            for attack in attacks:
                if attack.target != target_name and attack.target != "all":
                    continue
                    
                for defense_name, defense_class in defenses.items():
                    if self.current_spend >= self.config.budget:
                        print("Budget exceeded. Aborting.")
                        return

                    # Deterministic ID for resumability
                    run_id = hashlib.md5(f"{self.config.name}_{target_name}_{attack.id}_{defense_name}".encode()).hexdigest()
                    
                    try:
                        # Skip if already run
                        self.tracer.get_trace(run_id)
                        continue
                    except ValueError:
                        pass # Not run yet

                    # Apply defense wrapper
                    if defense_class:
                        if defense_name == "guard":
                            target = defense_class(base_target, base_target.llm)
                        else:
                            target = defense_class(base_target)
                    else:
                        target = base_target

                    # Run experiment
                    base_target.run_id = run_id
                    
                    trace = target.run(task_id=attack.id, task_desc=attack.payload)
                    
                    verdict = self.grader.grade(trace, attack)
                    
                    self.current_spend += trace.total_cost
                    self.tracer.save_trace(trace)