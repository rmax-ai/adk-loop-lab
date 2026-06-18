# HANDOFF-9

## What was built

- `tests/fixtures/corpus/`
  - Added a four-document local markdown corpus covering durable SQLite state,
    in-memory session state, checkpointing, and memory systems.

- `src/adk_loop_lab/examples/level_2_research/corpus.py`
  - Added `CorpusStore` with markdown loading, heading-based title extraction,
    simple keyword scoring, and document lookup by `doc_id`.

- `src/adk_loop_lab/examples/level_2_research/research.py`
  - Added serializable research-domain dataclasses and `ResearchTracker`.
  - Added default question formulation, claim/evidence matrix rendering, and
    final markdown report generation with `[source:doc_id]` citations.

- `src/adk_loop_lab/examples/level_2_research/example.py`
  - Added the bounded evidence-driven research loop using `LoopController`.
  - Wired the fake model path to deterministic corpus-backed claim extraction.
  - Kept persisted tracker state JSON-safe by storing a plain dict snapshot in
    `LoopState.facts["tracker"]`.

## Notes

- The coverage evaluator is implemented as a standard `EvaluationResult`
  producer so it fits the existing controller contract.
- The example follows the Level 1 pattern and avoids any live web access or new
  dependencies.
