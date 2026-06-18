"""CLI for adk-loop-lab."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from adk_loop_lab.config import get_api_key, get_model_name, get_state_dir
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.models import LoopRun, LoopState
from adk_loop_lab.state.sqlite import SqliteStateStore

EXAMPLE_MAP: dict[str, str] = {
    "level-1": "level_1_refinement",
    "level-2": "level_2_research",
    "level-3": "level_3_coding_fleet",
}


@click.group()
def main() -> None:
    """adk-loop-lab - Agentic Loop Engineering Reference Repository."""


@main.command()
def examples() -> None:
    """List available examples."""
    click.echo("Available examples:")
    click.echo("  level-1    Bounded document refinement (generator-critic)")
    click.echo("  level-2    Evidence-driven research (parallel + citations)")
    click.echo("  level-3    Multi-agent coding loop (sandbox + resume)")
    click.echo()
    click.echo("Run with: uv run adk-loop run <example>")


@main.command()
@click.argument("example")
@click.option("--offline", is_flag=True, help="Use fake model (no API credentials)")
@click.option("--model", default=None, help="Override model name")
@click.option("--max-iterations", default=None, type=int, help="Override max iterations")
def run(example: str, offline: bool, model: str | None, max_iterations: int | None) -> None:
    """Run an example loop."""
    run_example_cli(
        example,
        offline=offline,
        model_name=model,
        max_iterations=max_iterations,
    )


def run_example_cli(
    example: str,
    *,
    offline: bool = True,
    model_name: str | None = None,
    max_iterations: int | None = None,
) -> None:
    """Run an example from the CLI."""
    resolved_example = EXAMPLE_MAP.get(example)
    if resolved_example is None:
        click.echo(f"Unknown example: {example}", err=True)
        click.echo("Available: level-1, level-2, level-3", err=True)
        raise SystemExit(1)

    use_fake_model = offline
    if not use_fake_model and get_api_key() is None:
        click.echo("GOOGLE_API_KEY is not set; falling back to offline mode.", err=True)
        use_fake_model = True

    state_dir = Path(get_state_dir())
    base_dir = str(state_dir / "runs")
    db_path = str(state_dir / "state" / f"{resolved_example}.db")
    selected_model = model_name or get_model_name()

    if resolved_example == "level_1_refinement":
        from adk_loop_lab.examples.level_1_refinement.example import run_example as run_level_1

        asyncio.run(
            run_level_1(
                use_fake_model=use_fake_model,
                base_dir=base_dir,
                db_path=db_path,
                model_name=selected_model,
                max_iterations=max_iterations,
            )
        )
        return

    if resolved_example == "level_2_research":
        from adk_loop_lab.examples.level_2_research.example import run_example as run_level_2

        asyncio.run(
            run_level_2(
                use_fake_model=use_fake_model,
                base_dir=base_dir,
                db_path=db_path,
                model_name=selected_model,
                max_iterations=max_iterations,
            )
        )
        return

    from adk_loop_lab.examples.level_3_coding_fleet.example import run_example as run_level_3

    asyncio.run(
        run_level_3(
            use_fake_model=use_fake_model,
            base_dir=base_dir,
            db_path=db_path,
            model_name=selected_model,
            max_iterations=max_iterations,
        )
    )


@main.command()
@click.argument("run_id")
def inspect(run_id: str) -> None:
    """Inspect a run's state and status."""
    run, state = asyncio.run(_load_run(run_id))
    if run is None:
        click.echo(f"Run not found: {run_id}", err=True)
        raise SystemExit(1)

    click.echo(f"Run ID: {run.run_id}")
    click.echo(f"Example: {run.example_id}")
    click.echo(f"Status: {run.status.value}")
    click.echo(f"Iteration: {run.current_iteration}/{run.max_iterations}")
    click.echo(f"Decision: {run.last_decision.value if run.last_decision else 'N/A'}")
    click.echo(f"Created: {run.created_at.isoformat()}")
    click.echo(f"Updated: {run.updated_at.isoformat()}")

    if state is not None:
        click.echo(f"Phase: {state.phase.value}")
        click.echo(f"Progress: {state.progress_score:.2f}")
        click.echo(f"Facts: {', '.join(sorted(state.facts.keys())) or '(none)'}")


@main.command()
@click.argument("run_id")
def events(run_id: str) -> None:
    """Show event log for a run."""
    recorder = EventRecorder(base_dir=str(Path(get_state_dir()) / "runs"))
    recorded_events = recorder.get_events(run_id)
    if not recorded_events:
        click.echo(f"No events found for run: {run_id}", err=True)
        raise SystemExit(1)

    for event in recorded_events:
        payload = json.dumps(event.payload, sort_keys=True)
        click.echo(
            f"{event.timestamp.isoformat()} "
            f"[iter={event.iteration}] {event.event_type.value} "
            f"actor={event.actor} payload={payload}"
        )


async def _load_run(run_id: str) -> tuple[LoopRun | None, LoopState | None]:
    """Load run metadata and state from the configured state directory."""
    state_root = Path(get_state_dir()) / "state"
    if not state_root.exists():
        return None, None

    for db_path in sorted(state_root.glob("*.db")):
        store = SqliteStateStore(str(db_path))
        await store.initialize()
        try:
            run = await store.get_run(run_id)
            if run is None:
                continue
            state = await store.get_state(run_id)
            return run, state
        finally:
            await store.close()

    return None, None


if __name__ == "__main__":
    sys.exit(main())
