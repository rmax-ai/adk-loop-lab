# Verification and Stopping

Reliable loops need two separate systems:

- verification, to decide whether the latest work is acceptable
- stopping, to decide whether the loop should continue at all

`adk-loop-lab` keeps both deterministic by default.

## Deterministic Evaluators

The reusable deterministic evaluators live in
[src/adk_loop_lab/evaluation/deterministic.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/evaluation/deterministic.py).
They currently include:

- `schema_validator()`
- `exact_match_validator()`
- `range_validator()`
- `list_contains_validator()`
- `not_contains_validator()`

These cover the kinds of checks described in the project spec:

- schema validation
- bounded numeric checks such as word count
- required or forbidden patterns
- exact textual requirements

Example 1 uses them in
[src/adk_loop_lab/examples/level_1_refinement/checks.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/checks.py):

```python
results.append(range_validator(word_count, 180, 260, "word_count"))
results.append(
    not_contains_validator(
        normalized,
        ["according to", "studies show", "research indicates", "experts agree"],
        "unsupported_citations",
    )
)
```

Those checks enforce word count and forbidden citation phrasing without asking a
model to judge them.

## Model-Based Evaluators

Model-based evaluators are supported by the same `EvaluationResult` contract in
[src/adk_loop_lab/models/evaluations.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/evaluations.py),
but they set `is_deterministic=False`.

Example 1's critic is the clearest current example:

- `evaluate_critic()` in
  [src/adk_loop_lab/examples/level_1_refinement/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/example.py)
  parses a model-produced JSON score and returns `EvaluationResult`
- that evaluator is used for qualitative review such as clarity and revision
  feedback

This is where checks like clarity, coherence, and coverage belong when they
cannot be reduced to deterministic rules.

## Composite Evaluator Policies

Composite policies are defined by `CompositePolicy` in
[src/adk_loop_lab/models/evaluations.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/evaluations.py)
and implemented in
[src/adk_loop_lab/evaluation/composite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/evaluation/composite.py).

The supported policies are:

- `DETERMINISTIC_VETO`
- `ALL_REQUIRED`
- `WEIGHTED_SCORE`
- `QUORUM`

### `DETERMINISTIC_VETO`

If any deterministic evaluator fails, the composite result fails immediately.
This is the default policy and matches the project's "verification first"
principle.

### `ALL_REQUIRED`

Every evaluator must pass.

### `WEIGHTED_SCORE`

The current implementation uses average score and passes at `>= 0.7`.

### `QUORUM`

More than half of evaluators must pass.

## Stopping Conditions

Terminal and continuation decisions are modeled by `Decision` in
[src/adk_loop_lab/models/state.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/state.py).
The terminal set is defined in
[src/adk_loop_lab/loop/lifecycle.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/lifecycle.py).

Important outcomes:

- `SUCCESS`
- `FAILED`
- `BLOCKED`
- `BUDGET_EXHAUSTED`
- `STAGNATED`
- `CONTINUE`

The stopping logic itself is in `StoppingPolicy.evaluate()` in
[src/adk_loop_lab/loop/policies.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/policies.py).

The current decision order is:

1. fail on fatal error
2. succeed if all criteria are met
3. stop on budget exhaustion
4. stop on stagnation
5. stop on duration exhaustion
6. otherwise continue

## How Verification Feeds Stopping

Inside `LoopController._verify()`:

- evaluator results are normalized to `EvaluationResult`
- `progress_score` becomes the average score for this iteration
- evaluation IDs are appended to `state.evaluation_history`
- `_all_criteria_met` is set when all evaluators passed
- stagnation count is reset or incremented based on `progress_score`

Then `LoopController._decide()` hands `_all_criteria_met`,
`stagnation_count`, and the current `BudgetManager` state to
`StoppingPolicy`.

## Real Examples in the Repo

- document refinement: deterministic draft checks plus model critic in
  `src/adk_loop_lab/examples/level_1_refinement/`
- evidence research: deterministic coverage evaluator in
  [src/adk_loop_lab/examples/level_2_research/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_2_research/example.py)
- coding fleet: deterministic test and requirement evaluators in
  [src/adk_loop_lab/examples/level_3_coding_fleet/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_3_coding_fleet/example.py)
