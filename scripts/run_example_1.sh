#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" PYTHONPATH=src uv run python3 -c "
import asyncio
from adk_loop_lab.examples.level_1_refinement.example import run_example
asyncio.run(run_example(use_fake_model=True))
"
