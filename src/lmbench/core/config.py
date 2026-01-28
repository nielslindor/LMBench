import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class BenchmarkConfig(BaseModel):
    rounds: int = 1
    matrix: bool = False
    deep: bool = False
    context_length: int = 2048
    gpu_offload: Optional[int] = None
    default_prompt: str = "Write a 200-word essay about the future of local AI."
    models_to_pull: List[str] = Field(default_factory=list)

class ConfigManager:
    def __init__(self):
        self.config_path = Path.home() / ".lmbench" / "config.json"
        self._ensure_dir()

    def _ensure_dir(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, config: BenchmarkConfig):
        with open(self.config_path, "w") as f:
            f.write(config.model_dump_json(indent=2))

    def load(self) -> BenchmarkConfig:
        if not self.config_path.exists():
            return BenchmarkConfig()
        try:
            with open(self.config_path, "r") as f:
                return BenchmarkConfig.model_validate_json(f.read())
        except Exception:
            return BenchmarkConfig()
