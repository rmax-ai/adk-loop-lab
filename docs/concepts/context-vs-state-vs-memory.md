# Context vs State vs Memory

`adk-loop-lab` separates three things that agent projects often blur together:
context, state, and memory. The distinction matters because each one has a
different trust model and lifetime.

## Context

Context is what the model sees in the current iteration. In this repo, context
is built fresh each time by `ContextBuilder` in
[src/adk_loop_lab/context/builder.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/context/builder.py).

`ContextBuilder.build_plan_context()` assembles:

- the run goal
- acceptance criteria
- current constraints
- current phase and progress
- pending actions
- authoritative observations from `LoopState.facts`
- verified memories
- recent failures
- budget status

It also emits a context manifest describing what was included and what was
omitted.

Example shape:

```python
builder = ContextBuilder(max_memory_items=5, max_failure_items=3)
prompt = builder.build_plan_context(run, state)
```

The point of context is not permanence. It is a bounded, reconstructed view for
this iteration only.

## State

State is the authoritative current record of the run. It lives in
`LoopRun` and `LoopState` in
[src/adk_loop_lab/models/state.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/state.py)
and is persisted by
[src/adk_loop_lab/state/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/state/sqlite.py).

`LoopState` stores facts such as:

- `phase`
- `facts`
- `constraints`
- `completed_actions`
- `pending_actions`
- `failed_attempts`
- `evaluation_history`
- `progress_score`
- `stagnation_count`

State is read and updated every iteration by
[src/adk_loop_lab/loop/controller.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/controller.py).
The control plane trusts state before any remembered lesson or model summary.

Example:

```python
state = LoopState(
    facts={
        "draft": "",
        "draft_history": [],
        "critique_history": [],
        "revision_count": 0,
    }
)
```

That is the initial state for the refinement example in
[src/adk_loop_lab/examples/level_1_refinement/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/example.py).

## Memory

Memory is learned knowledge promoted from observations or outcomes after
verification. It is represented by `MemoryRecord` in
[src/adk_loop_lab/models/memory.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/memory.py)
and stored through the `MemoryStore` interface in
[src/adk_loop_lab/memory/base.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/base.py).

The default implementation is SQLite FTS5 in
[src/adk_loop_lab/memory/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/sqlite.py).
Promotion policy lives in
[src/adk_loop_lab/memory/promotion.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/promotion.py).

Memory has a lifecycle:

- `CANDIDATE`
- `VERIFIED`
- `REJECTED`
- `STALE`
- `INVALIDATED`

Promotion is evidence-gated:

```python
record = await promoter.add_candidate(
    kind=MemoryKind.LESSON,
    content="Word-count checks caught overlong drafts early.",
    source_run_id=run.run_id,
    source_iteration=run.current_iteration,
    confidence=0.8,
)
promoted = await promoter.try_promote(record, evidence_refs=["eval:word_count"])
```

## When to Use Each

- Use context for the current model invocation
- Use state for current facts that must survive restarts and guide control
  decisions
- Use memory for reusable lessons or failures that were verified strongly
  enough to retain

## Anti-Patterns

### Treating Context as State

Do not assume that because a model saw something in the previous iteration, the
system still "knows" it. The controller is designed to rebuild from current
state, not prior prompt history.

### Treating Memory as Authoritative State

Do not rely on a past memory record for current facts when `LoopState` can be
read directly. This is why the research example persists its tracker in
`state.facts["tracker"]` instead of trying to reconstruct the active report
from memory alone:

- tracker restore and persist helpers live in
  [src/adk_loop_lab/examples/level_2_research/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_2_research/example.py)

### Stuffing Everything into `facts`

`LoopState.facts` is flexible, but it is still state, not an unbounded prompt
dump. `ContextBuilder` exists so prompts can stay selective and bounded.

## Practical Code References

- context assembly: `src/adk_loop_lab/context/builder.py`
- state models: `src/adk_loop_lab/models/state.py`
- state persistence: `src/adk_loop_lab/state/sqlite.py`
- memory interface: `src/adk_loop_lab/memory/base.py`
- memory storage: `src/adk_loop_lab/memory/sqlite.py`
- memory promotion: `src/adk_loop_lab/memory/promotion.py`
