.PHONY: help install lint format typecheck test clean examples

UV_CACHE_DIR ?= /tmp/uv-cache

help:
	@echo "adk-loop-lab"
	@echo ""
	@echo "  make install     Install dependencies"
	@echo "  make lint        Run ruff linter"
	@echo "  make format      Run ruff formatter"
	@echo "  make typecheck   Run mypy type checker"
	@echo "  make test        Run all tests"
	@echo "  make examples    Run all examples (offline mode)"
	@echo "  make clean       Remove build artifacts"

install:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --extra dev

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run ruff check src/ tests/

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run ruff format src/ tests/

typecheck:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run mypy src/

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run pytest tests/ -v

examples:
	@echo "=== Example 1: Document Refinement ==="
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run python3 -c "import asyncio; from adk_loop_lab.examples.level_1_refinement.example import run_example; asyncio.run(run_example(use_fake_model=True))"
	@echo ""
	@echo "=== Example 2: Evidence Research ==="
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run python3 -c "import asyncio; from adk_loop_lab.examples.level_2_research.example import run_example; asyncio.run(run_example(use_fake_model=True))"
	@echo ""
	@echo "=== Example 3: Coding Fleet ==="
	UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=src uv run python3 -c "import asyncio; from adk_loop_lab.examples.level_3_coding_fleet.example import run_example; asyncio.run(run_example(use_fake_model=True))"

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache var/runs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
