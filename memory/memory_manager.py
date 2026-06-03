from pathlib import Path
import json


class MemoryManager:

    def __init__(self):
        self.memory_file = Path("memory/memory.json")

    def load(self):

        if not self.memory_file.exists():
            return {}

        with open(self.memory_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data):

        self.memory_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )