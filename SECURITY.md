# Security Policy

## Supported Versions

`adk-loop-lab` is currently supported on the active `main` branch. Security
fixes are developed and released from the latest code in this repository.

## Reporting a Vulnerability

Report suspected vulnerabilities to `me@rmax.io`.

- Initial response target: within 48 hours
- Coordinated disclosure target: within 90 days of acknowledgement
- Include reproduction steps, impact, affected files or modules, and any
  proposed mitigations if available

Please do not open public GitHub issues for unpatched vulnerabilities.

## Security Design Principles

This repository is a reference implementation for controlled agentic loops, so
the codebase deliberately keeps several safety boundaries deterministic:

- Deterministic shell controls: sandboxed shell execution is allowlisted in
  [src/adk_loop_lab/tools/shell.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/shell.py)
- Tool safety metadata: tool effect levels and approval requirements live in
  [src/adk_loop_lab/tools/safety.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/safety.py)
- Path confinement: filesystem access is confined by
  [src/adk_loop_lab/tools/filesystem.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/filesystem.py)
  and shell argument validation in
  [src/adk_loop_lab/tools/shell.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/shell.py)
- No secrets in traces: runtime traces are intended to avoid credential
  disclosure, with ADK callback redaction isolated in
  [src/adk_loop_lab/adk/callbacks.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/callbacks.py)
- Deterministic state persistence and resume: state and checkpoints are written
  through
  [src/adk_loop_lab/state/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/state/sqlite.py),
  [src/adk_loop_lab/state/transactions.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/state/transactions.py),
  and
  [src/adk_loop_lab/loop/checkpoints.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/checkpoints.py)

## Secrets and Credentials

This repository does not provide secrets management infrastructure.

- Use [.env.example](/home/rmax-10/src/adk-loop-lab/.env.example) as the setup
  template
- Never commit real API keys, tokens, or `.env` files with live credentials
- Do not store secrets in fixtures, event traces, checkpoints, or memory
  records

If you believe a secret has been committed, rotate it immediately and report
the exposure to `me@rmax.io`.
