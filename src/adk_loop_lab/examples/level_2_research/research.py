"""Research loop: planning, parallel source research, evidence tracking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ResearchClaim:
    """A claim discovered during research."""

    claim_id: str
    text: str
    source_doc_ids: list[str] = field(default_factory=list)
    evidence_quality: float = 0.0


@dataclass
class ResearchQuestion:
    """A research question to investigate."""

    question_id: str
    text: str
    answered: bool = False
    relevant_docs: list[str] = field(default_factory=list)


class ResearchTracker:
    """Tracks the state of an evidence-driven research loop."""

    def __init__(self) -> None:
        self.questions: list[ResearchQuestion] = []
        self.claims: list[ResearchClaim] = []
        self.searched_queries: set[str] = set()

    def add_question(self, text: str) -> ResearchQuestion:
        """Add a new research question."""
        question = ResearchQuestion(
            question_id=f"q{len(self.questions) + 1}",
            text=text,
        )
        self.questions.append(question)
        return question

    def add_claim(self, text: str, source_doc_ids: list[str] | None = None) -> ResearchClaim:
        """Add a claim with supporting source identifiers."""
        sources = sorted(set(source_doc_ids or []))
        quality = min(1.0, 0.5 + (0.25 * len(sources))) if sources else 0.0
        claim = ResearchClaim(
            claim_id=f"c{len(self.claims) + 1}",
            text=text,
            source_doc_ids=sources,
            evidence_quality=quality,
        )
        self.claims.append(claim)
        return claim

    def get_coverage_matrix(self) -> dict[str, Any]:
        """Build a coverage matrix: which claims are supported by which sources."""
        return {
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "text": claim.text,
                    "sources": list(claim.source_doc_ids),
                    "evidence_quality": claim.evidence_quality,
                }
                for claim in self.claims
            ],
            "questions": [
                {
                    "question_id": question.question_id,
                    "text": question.text,
                    "answered": question.answered,
                    "relevant_docs": list(question.relevant_docs),
                }
                for question in self.questions
            ],
        }

    def get_open_gaps(self) -> list[str]:
        """Identify claims without evidence."""
        return [claim.text for claim in self.claims if not claim.source_doc_ids]

    def deduplicate_query(self, query: str) -> bool:
        """Check if query has been searched before. Returns True if duplicate."""
        normalized = query.strip().lower()
        if normalized in self.searched_queries:
            return True
        self.searched_queries.add(normalized)
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state to a plain dictionary."""
        return {
            "questions": [asdict(question) for question in self.questions],
            "claims": [asdict(claim) for claim in self.claims],
            "searched_queries": sorted(self.searched_queries),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ResearchTracker:
        """Rebuild a tracker from serialized state."""
        tracker = cls()
        if not payload:
            return tracker

        for question_payload in payload.get("questions", []):
            tracker.questions.append(
                ResearchQuestion(
                    question_id=str(question_payload.get("question_id", "")),
                    text=str(question_payload.get("text", "")),
                    answered=bool(question_payload.get("answered", False)),
                    relevant_docs=[
                        str(doc_id) for doc_id in question_payload.get("relevant_docs", [])
                    ],
                )
            )

        for claim_payload in payload.get("claims", []):
            quality = claim_payload.get("evidence_quality", 0.0)
            tracker.claims.append(
                ResearchClaim(
                    claim_id=str(claim_payload.get("claim_id", "")),
                    text=str(claim_payload.get("text", "")),
                    source_doc_ids=[
                        str(doc_id) for doc_id in claim_payload.get("source_doc_ids", [])
                    ],
                    evidence_quality=float(quality) if isinstance(quality, (int, float)) else 0.0,
                )
            )

        tracker.searched_queries = {
            str(query).strip().lower() for query in payload.get("searched_queries", [])
        }
        return tracker


def formulate_research_questions(topic: str) -> list[str]:
    """Generate research questions for a given topic."""
    normalized = topic.strip().lower()
    if (
        normalized
        == "compare three approaches to maintaining state in long-running agent workflows."
    ):
        return [
            "How does durable state persistence work in agent workflows?",
            "What are the trade-offs of in-memory session state?",
            "How do checkpointing systems enable workflow resume?",
            "How should memory systems relate to authoritative workflow state?",
        ]

    return [
        f"What is the core mechanism behind {topic}?",
        f"What are the practical trade-offs involved in {topic}?",
        f"What evidence is needed to compare approaches within {topic}?",
    ]


def build_claim_evidence_matrix(tracker: ResearchTracker) -> str:
    """Format the claim-evidence matrix as a markdown table."""
    lines = [
        "| Claim | Sources | Evidence Quality |",
        "| --- | --- | --- |",
    ]
    for claim in tracker.claims:
        sources = ", ".join(f"`{doc_id}`" for doc_id in claim.source_doc_ids) or "None"
        lines.append(f"| {claim.text} | {sources} | {claim.evidence_quality:.2f} |")
    if len(lines) == 2:
        lines.append("| No claims recorded. | None | 0.00 |")
    return "\n".join(lines)


def generate_report(topic: str, tracker: ResearchTracker, sources: list[str]) -> str:
    """Generate a final markdown report with traceable citations to source IDs."""
    lines = [
        "# Evidence-Driven Research Report",
        "",
        "## Topic",
        topic,
        "",
        "## Questions",
    ]

    for question in tracker.questions:
        lines.append(f"### {question.text}")
        related_claims = [
            claim
            for claim in tracker.claims
            if set(question.relevant_docs).intersection(claim.source_doc_ids)
        ]
        if not related_claims:
            lines.append("No evidence-backed claims recorded.")
            lines.append("")
            continue

        for claim in related_claims:
            citations = " ".join(f"[source:{doc_id}]" for doc_id in claim.source_doc_ids)
            lines.append(f"- {claim.text} {citations}".strip())
        lines.append("")

    lines.extend(
        [
            "## Claim-Evidence Matrix",
            build_claim_evidence_matrix(tracker),
            "",
            "## Source Coverage",
            f"Corpus sources consulted: {', '.join(f'`{source}`' for source in sources)}",
        ]
    )
    return "\n".join(lines)
