from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """Loads AION configuration from a YAML file."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config_path = Path(config_path)

    def load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        return data
