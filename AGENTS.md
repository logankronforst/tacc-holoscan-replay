# AGENTS.md

## Purpose
Operate this repo as a Holoscan replay validation workspace for TACC.

## Scope
- Validate replay-mode Holoscan pipelines on TACC GPU nodes.
- Document what is and is not equivalent to live Sensor Bridge operation.

## Mandatory Limitation Statement
Do not claim live Sensor Bridge parity unless dedicated provisioning is confirmed.

## Required Outputs
1. `jobs/` with replay batch scripts.
2. `src/` with replay pipeline entrypoints.
3. `docs/` with explicit limits and observed performance.

## Validation
- Confirm replay input fidelity and timestamp handling.
- Confirm operator outputs and pipeline completion.
- Log deviations from live hardware behavior.
