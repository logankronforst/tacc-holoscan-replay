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

## GPU Allocation Efficiency (Mandatory)
- Treat GPU allocations as high-cost resources and avoid idle GPU walltime.
- Before submitting long runs, execute a short smoke job to validate paths, env, and outputs.
- Monitor GPU utilization and memory in every benchmark run (`nvidia-smi` logging in job output directory).
- Flag likely under-utilization when sustained GPU utilization is below 40% during intended heavy stages.
- Flag likely over-utilization when utilization is pinned near 100% with elevated tail latency, OOM events, or retries.
- Prefer parameter sweeps that quantify efficiency (throughput per GPU-hour), not only raw throughput.
- Document wasted/idle time causes (data staging, startup overhead, queue strategy) in `docs/`.
