import yaml
import os
from pathlib import Path
from typing import List
from agentprobe.schemas import Attack

def load_seeds(seeds_dir: str = None) -> List[Attack]:
    if seeds_dir is None:
        # Default to the seeds folder next to this file
        seeds_dir = os.path.join(os.path.dirname(__file__), "seeds")
    
    attacks = []
    seeds_path = Path(seeds_dir)
    
    if not seeds_path.exists():
        return attacks

    for yaml_file in seeds_path.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)    
            if data:
                for item in data:
                    attacks.append(Attack(**item))
                    
    return attacks