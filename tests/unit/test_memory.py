"""Tests for memory system."""

import pytest

from adk_loop_lab.memory.sqlite import SqliteMemoryStore
from adk_loop_lab.memory.promotion import MemoryPromoter
from adk_loop_lab.models.memory import MemoryKind, MemoryRecord, MemoryStatus


@pytest.fixture
async def store() -> SqliteMemoryStore:
    s = SqliteMemoryStore(":memory:")
    await s.initialize()
    return s


class TestSqliteMemoryStore:
    async def test_add_and_get(self, store: SqliteMemoryStore) -> None:
        rec = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="test lesson",
            source_run_id="r1",
            source_iteration=0,
        )
        mid = await store.add(rec)
        loaded = await store.get(mid)
        assert loaded is not None
        assert loaded.content == "test lesson"

    async def test_search_finds_content(self, store: SqliteMemoryStore) -> None:
        rec = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="deterministic verification is essential",
            source_run_id="r1",
            source_iteration=0,
        )
        await store.add(rec)

        results = await store.search("verification", limit=5)
        assert len(results) >= 1

    async def test_search_no_match(self, store: SqliteMemoryStore) -> None:
        results = await store.search("nonexistent", limit=5)
        assert results == []

    async def test_promote(self, store: SqliteMemoryStore) -> None:
        rec = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="test",
            source_run_id="r1",
            source_iteration=0,
        )
        mid = await store.add(rec)
        ok = await store.promote(mid, ["evidence-1"])
        assert ok

        promoted = await store.get(mid)
        assert promoted is not None
        assert promoted.status == MemoryStatus.VERIFIED

    async def test_promote_nonexistent(self, store: SqliteMemoryStore) -> None:
        ok = await store.promote("nonexistent", [])
        assert not ok

    async def test_invalidate(self, store: SqliteMemoryStore) -> None:
        rec = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="test",
            source_run_id="r1",
            source_iteration=0,
        )
        mid = await store.add(rec)
        ok = await store.invalidate(mid, "superseded")
        assert ok

        invalidated = await store.get(mid)
        assert invalidated is not None
        assert invalidated.status == MemoryStatus.INVALIDATED

    async def test_close(self, store: SqliteMemoryStore) -> None:
        await store.close()
        await store.close()  # Safe to call twice


class TestMemoryPromoter:
    async def test_add_candidate(self, store: SqliteMemoryStore) -> None:
        promoter = MemoryPromoter(store)
        cand = await promoter.add_candidate(
            MemoryKind.LESSON, "test lesson", "r1", 0, confidence=0.7
        )
        assert cand.status == MemoryStatus.CANDIDATE

    async def test_try_promote_success(self, store: SqliteMemoryStore) -> None:
        promoter = MemoryPromoter(store, min_confidence=0.5)
        cand = await promoter.add_candidate(
            MemoryKind.LESSON, "test", "r1", 0, confidence=0.8
        )
        ok = await promoter.try_promote(cand, ["evidence-1"])
        assert ok

        promoted = await store.get(cand.memory_id)
        assert promoted is not None
        assert promoted.status == MemoryStatus.VERIFIED

    async def test_try_promote_no_evidence(self, store: SqliteMemoryStore) -> None:
        promoter = MemoryPromoter(store)
        cand = await promoter.add_candidate(
            MemoryKind.LESSON, "test", "r1", 0, confidence=0.8
        )
        ok = await promoter.try_promote(cand, [])  # No evidence
        assert not ok

    async def test_try_promote_low_confidence(self, store: SqliteMemoryStore) -> None:
        promoter = MemoryPromoter(store, min_confidence=0.7)
        cand = await promoter.add_candidate(
            MemoryKind.LESSON, "test", "r1", 0, confidence=0.3
        )
        ok = await promoter.try_promote(cand, ["evidence-1"])
        assert not ok
