from datetime import datetime
from pathlib import Path
from typing import Any
import json


class MemoryManager:
    """
    Manages persistent and temporary memory for AION.

    Persistent memory is stored in JSON.
    Temporary memory lives only during the current AION session.
    """

    def __init__(self, memory_file: str = "aion/memory/memory.json") -> None:
        self.memory_file = Path(memory_file)
        self.temporary_memory: dict[str, Any] = {}
        self.persistent_memory = self.load()

    def load(self) -> dict[str, Any]:
        if not self.memory_file.exists():
            return {}

        with self.memory_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        with self.memory_file.open("w", encoding="utf-8") as file:
            json.dump(
                self.persistent_memory,
                file,
                indent=4,
                ensure_ascii=False
            )

    def remember(self, key: str, value: Any, memory_type: str = "info") -> None:
        self.persistent_memory[key] = {
            "type": memory_type,
            "value": value,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.save()

    def recall(self, key: str) -> Any | None:
        item = self.persistent_memory.get(key)

        if item is None:
            return None

        return item.get("value")

    def forget(self, key: str) -> bool:
        if key not in self.persistent_memory:
            return False

        del self.persistent_memory[key]
        self.save()
        return True

    def list_memory(self) -> dict[str, Any]:
        return self.persistent_memory

    def remember_temp(self, key: str, value: Any) -> None:
        self.temporary_memory[key] = {
            "value": value,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    def recall_temp(self, key: str) -> Any | None:
        item = self.temporary_memory.get(key)

        if item is None:
            return None

        return item.get("value")