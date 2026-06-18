"""Tests for Example 2 — evidence-driven research loop."""

from pathlib import Path

from adk_loop_lab.examples.level_2_research.corpus import CorpusStore
from adk_loop_lab.examples.level_2_research.research import (
    ResearchTracker,
    formulate_research_questions,
)


class TestCorpusStore:
    @staticmethod
    def _corpus_path() -> Path:
        return Path(__file__).parents[2] / "tests" / "fixtures" / "corpus"

    def test_load_corpus(self) -> None:
        store = CorpusStore(str(self._corpus_path()))
        docs = store.load()
        assert len(docs) >= 3

    def test_search_finds_document(self) -> None:
        store = CorpusStore(str(self._corpus_path()))
        store.load()
        results = store.search("state", limit=3)
        assert len(results) >= 1

    def test_get_by_id(self) -> None:
        store = CorpusStore(str(self._corpus_path()))
        store.load()
        doc = store.get("state_persistence")
        assert doc is not None
        assert "durable" in doc.content.lower()

    def test_search_no_match(self) -> None:
        store = CorpusStore(str(self._corpus_path()))
        store.load()
        results = store.search("zzzznonexistent", limit=3)
        assert results == []


class TestResearchTracker:
    def test_add_question(self) -> None:
        tracker = ResearchTracker()
        q = tracker.add_question("How does durable state work?")
        assert q.text == "How does durable state work?"
        assert not q.answered

    def test_add_claim(self) -> None:
        tracker = ResearchTracker()
        c = tracker.add_claim("State is durable.", ["state_persistence"])
        assert c.text == "State is durable."
        assert "state_persistence" in c.source_doc_ids

    def test_get_open_gaps(self) -> None:
        tracker = ResearchTracker()
        tracker.add_claim("Claim without sources", [])
        gaps = tracker.get_open_gaps()
        assert len(gaps) == 1  # Claim with no sources

    def test_deduplicate_query(self) -> None:
        tracker = ResearchTracker()
        assert not tracker.deduplicate_query("state persistence")
        assert tracker.deduplicate_query("state persistence")

    def test_formulate_questions(self) -> None:
        questions = formulate_research_questions("test topic")
        assert len(questions) >= 3
        assert all(isinstance(q, str) for q in questions)
