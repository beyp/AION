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

    # Chemin absolu par defaut — fonctionne peu importe le repertoire courant
    _DEFAULT_MEMORY_FILE = Path(__file__).parent / "memory.json"

    def __init__(self, memory_file: str | None = None) -> None:
        if memory_file is None:
            self.memory_file = self._DEFAULT_MEMORY_FILE
        else:
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
        now = datetime.now().isoformat(timespec="seconds")
        existing = self.persistent_memory.get(key, {})

        self.persistent_memory[key] = {
            "type": memory_type,
            "value": value,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }

        self.save()

    def recall(self, key: str) -> Any | None:
        item = self.persistent_memory.get(key)

        if item is None:
            return None

        return item.get("value")

    def get_item(self, key: str) -> dict[str, Any] | None:
        return self.persistent_memory.get(key)

    def forget(self, key: str) -> bool:
        if key not in self.persistent_memory:
            return False

        del self.persistent_memory[key]
        self.save()
        return True

    def list_memory(self, memory_type: str | None = None) -> dict[str, Any]:
        if memory_type is None:
            return self.persistent_memory

        return {
            key: item
            for key, item in self.persistent_memory.items()
            if item.get("type") == memory_type
        }

    def search(self, query: str) -> dict[str, Any]:
        normalized_query = query.lower().strip()

        if not normalized_query:
            return {}

        results = {}

        for key, item in self.persistent_memory.items():
            value = str(item.get("value", ""))
            memory_type = str(item.get("type", ""))

            searchable_text = " ".join(
                [
                    key.lower(),
                    value.lower(),
                    memory_type.lower(),
                ]
            )

            if normalized_query in searchable_text:
                results[key] = item

        return results

    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}

        for item in self.persistent_memory.values():
            memory_type = item.get("type", "unknown")
            by_type[memory_type] = by_type.get(memory_type, 0) + 1

        return {
            "total": len(self.persistent_memory),
            "by_type": by_type,
            "temporary_total": len(self.temporary_memory),
        }

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
