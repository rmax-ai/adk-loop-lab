"""Corpus discovery and retrieval for the research example."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Document(NamedTuple):
    """A loaded corpus document."""

    doc_id: str
    title: str
    content: str
    source_path: str


class CorpusStore:
    """Manages a local corpus of documents for research."""

    def __init__(self, corpus_dir: str) -> None:
        self._corpus_dir = Path(corpus_dir)
        self._documents: list[Document] = []

    def load(self) -> list[Document]:
        """Load all markdown documents from the corpus directory."""
        documents: list[Document] = []
        for path in sorted(self._corpus_dir.rglob("*.md")):
            content = path.read_text(encoding="utf-8").strip()
            title = self._extract_title(path, content)
            documents.append(
                Document(
                    doc_id=path.stem,
                    title=title,
                    content=content,
                    source_path=str(path),
                )
            )
        self._documents = documents
        return list(self._documents)

    def search(self, query: str, limit: int = 5) -> list[Document]:
        """Simple keyword search across documents."""
        if not self._documents:
            self.load()

        keywords = [part for part in query.lower().split() if part]
        if not keywords:
            return self.list_all()[:limit]

        scored: list[tuple[int, Document]] = []
        for document in self._documents:
            haystack = f"{document.title}\n{document.content}".lower()
            score = sum(haystack.count(keyword) for keyword in keywords)
            if score > 0:
                scored.append((score, document))

        scored.sort(key=lambda item: (-item[0], item[1].doc_id))
        return [document for _, document in scored[:limit]]

    def get(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        if not self._documents:
            self.load()

        for document in self._documents:
            if document.doc_id == doc_id:
                return document
        return None

    def list_all(self) -> list[Document]:
        """List all loaded documents."""
        if not self._documents:
            self.load()
        return list(self._documents)

    def _extract_title(self, path: Path, content: str) -> str:
        """Extract a title from the first markdown heading or filename."""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return path.stem.replace("_", " ").title()
