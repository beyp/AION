"""Tests unitaires pour le MemoryManager."""
import json
import pytest
from aion.memory.memory_manager import MemoryManager


@pytest.fixture
def tmp_memory(tmp_path):
    memory_file = tmp_path / "memory.json"
    return MemoryManager(memory_file=str(memory_file))


def test_remember_and_recall(tmp_memory):
    tmp_memory.remember("host", "192.168.1.1", memory_type="network")
    assert tmp_memory.recall("host") == "192.168.1.1"


def test_remember_persists_to_disk(tmp_memory):
    tmp_memory.remember("key1", "value1")
    raw = json.loads(tmp_memory.memory_file.read_text(encoding="utf-8"))
    assert "key1" in raw
    assert raw["key1"]["value"] == "value1"


def test_recall_missing_key_returns_none(tmp_memory):
    assert tmp_memory.recall("nonexistent") is None


def test_forget(tmp_memory):
    tmp_memory.remember("to_delete", "bye")
    assert tmp_memory.forget("to_delete") is True
    assert tmp_memory.recall("to_delete") is None


def test_forget_missing_key_returns_false(tmp_memory):
    assert tmp_memory.forget("ghost") is False


def test_list_memory_all(tmp_memory):
    tmp_memory.remember("a", "1", memory_type="info")
    tmp_memory.remember("b", "2", memory_type="path")
    result = tmp_memory.list_memory()
    assert "a" in result
    assert "b" in result


def test_list_memory_by_type(tmp_memory):
    tmp_memory.remember("x", "val_x", memory_type="info")
    tmp_memory.remember("y", "val_y", memory_type="network")
    result = tmp_memory.list_memory(memory_type="info")
    assert "x" in result
    assert "y" not in result


def test_search_by_key(tmp_memory):
    tmp_memory.remember("server_ip", "10.0.0.1")
    results = tmp_memory.search("server")
    assert "server_ip" in results


def test_search_by_value(tmp_memory):
    tmp_memory.remember("gateway", "192.168.0.1")
    results = tmp_memory.search("192.168")
    assert "gateway" in results


def test_search_no_result(tmp_memory):
    tmp_memory.remember("alpha", "beta")
    results = tmp_memory.search("zzznomatch")
    assert results == {}


def test_stats(tmp_memory):
    tmp_memory.remember("k1", "v1", memory_type="info")
    tmp_memory.remember("k2", "v2", memory_type="info")
    tmp_memory.remember("k3", "v3", memory_type="path")
    tmp_memory.remember_temp("t1", "temp_val")
    stats = tmp_memory.stats()
    assert stats["total"] == 3
    assert stats["by_type"]["info"] == 2
    assert stats["by_type"]["path"] == 1
    assert stats["temporary_total"] == 1


def test_remember_temp_and_recall_temp(tmp_memory):
    tmp_memory.remember_temp("session_user", "pascal")
    assert tmp_memory.recall_temp("session_user") == "pascal"


def test_recall_temp_missing_returns_none(tmp_memory):
    assert tmp_memory.recall_temp("ghost") is None


def test_updated_at_changes_on_update(tmp_memory):
    tmp_memory.remember("mykey", "v1")
    created_at = tmp_memory.get_item("mykey")["created_at"]
    tmp_memory.remember("mykey", "v2")
    item = tmp_memory.get_item("mykey")
    assert item["value"] == "v2"
    assert item["created_at"] == created_at
