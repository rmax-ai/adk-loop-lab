"""Append-only JSONL event recording."""

from pathlib import Path

from adk_loop_lab.models import LoopEvent


class EventRecorder:
    """Append-only JSONL event recorder."""

    def __init__(self, base_dir: str = "var/runs") -> None:
        self._base_dir = Path(base_dir)

    def record(self, event: LoopEvent) -> None:
        """Write a single event to the run's JSONL file."""
        run_dir = self.get_run_dir(event.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        events_path = run_dir / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as file_handle:
            file_handle.write(f"{event.to_jsonl()}\n")

    def get_events(self, run_id: str) -> list[LoopEvent]:
        """Read all events for a run (for inspection)."""
        events_path = self.get_run_dir(run_id) / "events.jsonl"
        if not events_path.exists():
            return []

        events: list[LoopEvent] = []
        with events_path.open(encoding="utf-8") as file_handle:
            for line in file_handle:
                stripped_line = line.strip()
                if stripped_line:
                    events.append(LoopEvent.model_validate_json(stripped_line))
        return events

    def get_run_dir(self, run_id: str) -> Path:
        """Get the run's output directory."""
        return self._base_dir / run_id
