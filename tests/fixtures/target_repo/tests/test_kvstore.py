"""Tests for KVStore."""

from kvstore import KVStore


class TestKVStore:
    def test_set_and_get(self) -> None:
        store = KVStore()
        store.set("a", 1)
        assert store.get("a") == 1

    def test_get_missing(self) -> None:
        store = KVStore()
        assert store.get("nonexistent") is None

    def test_delete(self) -> None:
        store = KVStore()
        store.set("a", 1)
        assert store.delete("a")
        assert not store.delete("a")

    def test_exists(self) -> None:
        store = KVStore()
        store.set("a", 1)
        assert store.exists("a")
        assert not store.exists("b")

    def test_keys(self) -> None:
        store = KVStore()
        store.set("a", 1)
        store.set("b", 2)
        assert set(store.keys()) == {"a", "b"}
