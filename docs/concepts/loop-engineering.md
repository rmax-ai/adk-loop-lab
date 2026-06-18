# Loop Engineering

Loop engineering is the design of the deterministic outer system that keeps an
LLM useful over multiple iterations. In `adk-loop-lab`, that outer system lives
primarily in
[src/adk_loop_lab/loop/controller.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/controller.py)
and the supporting policy modules in `src/adk_loop_lab/loop/`.

## Loop vs Single Agent Call

A single agent call asks a model for one response and usually treats that
response as the output. A loop does more:

- reads durable state before each step
- rebuilds the current prompt from fresh inputs
- executes bounded work
- verifies outcomes
- persists state and checkpoints
- decides deterministically whether to continue

That distinction is visible in this project:

- ADK invocation is isolated in
  [src/adk_loop_lab/adk/runner.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/runner.py)
  and `src/adk_loop_lab/adk/agents.py`
- loop control is isolated in
  [src/adk_loop_lab/loop/controller.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/controller.py)

## The Seven-Phase Lifecycle

The lifecycle phases are defined by `Phase` in
[src/adk_loop_lab/models/state.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/state.py)
and ordered in
[src/adk_loop_lab/loop/lifecycle.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/lifecycle.py):

1. `DISCOVER`
2. `PLAN`
3. `EXECUTE`
4. `VERIFY`
5. `COMMIT`
6. `REFLECT`
7. `DECIDE`

`LoopController.run()` walks that sequence on every iteration. The
implementation makes the separation concrete:

```python
await self._run_phase(run, state, Phase.DISCOVER, self._discover)
await self._run_phase(run, state, Phase.PLAN, self._plan)
await self._run_phase(run, state, Phase.EXECUTE, self._execute)
await self._run_phase(run, state, Phase.VERIFY, self._verify)
await self._run_phase(run, state, Phase.COMMIT, self._commit)
await self._run_phase(run, state, Phase.REFLECT, self._reflect, buffer=False)
decision = await self._run_decide_phase(run, state)
```

That exact control flow lives in
[src/adk_loop_lab/loop/controller.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/controller.py).

## Deterministic Shell, Probabilistic Core

This repository follows the rule from `SPEC.md`: models propose; deterministic
code decides.

The probabilistic core:

- ADK agents created in
  [src/adk_loop_lab/adk/agents.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/agents.py)
- ADK execution through
  [src/adk_loop_lab/adk/runner.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/runner.py)

The deterministic shell:

- lifecycle ordering in
  [src/adk_loop_lab/loop/lifecycle.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/lifecycle.py)
- budget enforcement in
  [src/adk_loop_lab/loop/policies.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/policies.py)
- recovery and retry decisions in
  [src/adk_loop_lab/loop/recovery.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/recovery.py)
- atomic state commits in
  [src/adk_loop_lab/state/transactions.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/state/transactions.py)

`PLAN` and `REFLECT` may call a model. `DECIDE` never does.

## State vs Memory

Loop engineering needs both state and memory, but they serve different jobs.

- State is the current authoritative run snapshot:
  `LoopRun` and `LoopState` in
  [src/adk_loop_lab/models/state.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/state.py)
- Memory is learned knowledge that may outlive a single iteration or run:
  `MemoryRecord` in
  [src/adk_loop_lab/models/memory.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/memory.py)

In this repo, the loop reads state every iteration. Memory is optional,
searchable, and evidence-gated before promotion.

## Bounded Iteration

Every loop run carries explicit budgets through `BudgetConfig`:

```python
run = LoopRun(
    example_id="level_1_refinement",
    goal="Write a concise explanation of why deterministic verification is necessary.",
    budgets=BudgetConfig(
        max_iterations=5,
        max_model_calls=15,
        stagnation_threshold=3,
    ),
)
```

This pattern appears in
[src/adk_loop_lab/examples/level_1_refinement/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/example.py),
[src/adk_loop_lab/examples/level_2_research/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_2_research/example.py),
and
[src/adk_loop_lab/examples/level_3_coding_fleet/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_3_coding_fleet/example.py).

The controller uses `BudgetManager` and `StoppingPolicy` from
[src/adk_loop_lab/loop/policies.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/policies.py)
to stop on iteration, model-call, tool-call, duration, or stagnation limits.

## Verification-First Design

The project treats verification as a first-class phase, not an afterthought.

- deterministic validators are in
  [src/adk_loop_lab/evaluation/deterministic.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/evaluation/deterministic.py)
- composite evaluation policies are in
  [src/adk_loop_lab/evaluation/composite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/evaluation/composite.py)
- example-specific checks appear in
  [src/adk_loop_lab/examples/level_1_refinement/checks.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/checks.py)

Example 1 demonstrates the pattern directly. `check_draft()` combines word
count checks, example detection, generation-versus-verification checks, and
forbidden citation phrases before the loop decides whether the draft is good
enough.

## Checkpoint and Resume

Reliable loops need interruption tolerance. This repo checkpoints after each
committed iteration through
[src/adk_loop_lab/loop/checkpoints.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/checkpoints.py).

The controller's `_commit()` phase:

- writes run and state atomically via `TransactionManager.commit_iteration()`
- creates a checkpoint with `CheckpointManager.create_checkpoint()`

Resuming a run uses `LoopController.resume()` and
`CheckpointManager.resume_run()`. Corrupt latest checkpoints are skipped in
favor of the newest valid checkpoint, which is exercised in
[tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py).

## Code Anchors

- loop lifecycle: `src/adk_loop_lab/loop/controller.py`
- phase transitions: `src/adk_loop_lab/loop/lifecycle.py`
- budgets and stopping: `src/adk_loop_lab/loop/policies.py`
- recovery: `src/adk_loop_lab/loop/recovery.py`
- checkpoints: `src/adk_loop_lab/loop/checkpoints.py`
- per-iteration prompt assembly: `src/adk_loop_lab/context/builder.py`
- examples: `src/adk_loop_lab/examples/`
