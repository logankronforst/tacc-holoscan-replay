# TACC Holoscan Replay Technical Log and Benchmarking History

[TOC]

## Executive Summary
This document records the replay-mode validation and benchmarking campaign on TACC Vista, including job history, constraints, fixes, metrics, and interpretation.

Replay-mode pipeline execution is validated.
Live Sensor Bridge parity is not validated.

## Mandatory Limitation Statement
Do not claim live Sensor Bridge parity unless dedicated provisioning is confirmed.

## Validation Scope
Validated in this campaign:
- Replay input discovery and processing.
- Replay job orchestration (smoke, bench, sweep, aggregate).
- Output artifact generation (`metrics.json`, `gpu_metrics.csv`, `summary.csv`, `summary.md`).
- Timestamp-file ingestion and monotonicity checks.

Not validated in this campaign:
- Live sensor ingress equivalence.
- Hardware-timed ingest / PTP parity.
- Dedicated live Sensor Bridge behavior.

## Platform and Runtime
- System: TACC Vista.
- Account used: `CCR25007`.
- Partitions used in this campaign: `gh`, `gg`.
- GPU observed: NVIDIA GH200 120GB on nodes where telemetry is available.
- Replay input root: `/scratch/11039/logankronforst/replay_data`.
- Repo root: `/work/11039/logankronforst/vista/tacc-holoscan-replay`.

Runtime and submission policy notes:
- Vista `gh` rejects `--gres=gpu`; GPU resources are partition-policy controlled.
- Valid account string required uppercase (`CCR25007`).
- Scheduler output banner can appear before job id; robust parsing is required in helper scripts.

## Workflow Architecture
Primary chain:
1. `hs_replay_smoke`
2. `hs_replay_bench` (3 jobs)
3. `hs_replay_sweep`
4. `hs_replay_agg`

Artifacts by stage:
- Smoke: `results/smoke/<jobid>/metrics.json`, `gpu_metrics.csv`
- Bench: `results/bench/<jobid>/metrics.json`, `gpu_metrics.csv`
- Sweep: `results/sweep/<jobid>/mode_*.json`, `summary.csv`, `summary.md`, `gpu_metrics.csv`
- Aggregate: rewrites/produces `summary.csv` and `summary.md`

## Implemented Operational Fixes
Scheduler/submission fixes:
- Enforced valid account usage: `CCR25007`.
- Removed `--gres=gpu` assumptions for `gh` partition policy.
- Updated robust job id parsing in `jobs/submit_today.sh`.

Job script reliability fixes:
- Replaced noisy `module load python3 || true` with deterministic module load pattern and hard `python3` existence check.
- Increased `nvidia-smi` telemetry cadence from 5s to 500ms (`-lms 500`).

Synthetic GPU workload support (for efficiency probing):
- Added opt-in GPU workload flags in `src/replay_entrypoint.py`:
  - `--gpu-workload {none,matmul}`
  - `--gpu-backend {auto,cupy,torch}`
  - `--gpu-mat-size`, `--gpu-iters`, `--gpu-work-every-n`
- Exposed env-var wiring in:
  - `jobs/replay_benchmark.sbatch`
  - `jobs/replay_sweep.sbatch`

## Job History (Slurm Accounting)

### Original Campaign and Follow-up Validation
| Job ID | Role | State | Elapsed | Notes |
|---|---|---|---|---|
| 602525 | smoke (earlier run) | COMPLETED | 00:00:09 | Pre-chain smoke artifact present |
| 602526 | smoke gate | COMPLETED | 00:00:08 | Baseline chain smoke success |
| 602527 | bench | COMPLETED | 00:00:10 | `READ_MODE=full`, `TARGET_FPS=0` |
| 602528 | bench | COMPLETED | 00:00:36 | `READ_MODE=full`, `TARGET_FPS=30` |
| 602529 | bench | COMPLETED | 00:00:21 | `READ_MODE=metadata`, `TARGET_FPS=60` |
| 602530 | sweep | COMPLETED | 00:01:29 | `READ_MODES=metadata full`, `FPS_LIST=0 30 60` |
| 602532 | aggregate | COMPLETED | 00:00:07 | Generated `summary.csv` + `summary.md` |
| 603082 | smoke recheck | COMPLETED | 00:00:07 | Confirmed module-warning fix |
| 603086 | bench recheck | COMPLETED | 00:00:34 | Confirmed 500ms GPU sampling density |
| 603087 | timestamp validation | COMPLETED | 00:00:21 | `TIMESTAMPS_FILE` injected |
| 603088 | efficiency probe A | COMPLETED | 00:00:09 | `full`, unpaced |
| 603089 | efficiency probe B | COMPLETED | 00:00:34 | `full`, 30 FPS |
| 603090 | efficiency probe C | COMPLETED | 00:00:06 | `metadata`, unpaced |
| 603104 | synthetic GPU probe | COMPLETED | 00:00:17 | `GPU_WORKLOAD=matmul`, backend auto |
| 604242 | replay chain (matmul enabled) | FAILED | 00:00:28 | `cupy` missing, and `torch` CUDA unavailable for synthetic workload |
| 604243 | replay chain (submit typo) | FAILED | 00:00:09 | `INPUT_DIR` typo prevented `replay_entrypoint.py` from starting |
| 604244 | replay chain (gg, none) | COMPLETED | 00:00:30 | smoke + unpaced full + paced + GPU slot (no workload) |
| 604249 | replay chain (gg, none) | COMPLETED | 00:00:31 | same profile as 604244; no `gpu_metrics.csv` produced |
| 604250 | replay chain (gg, none) | COMPLETED | 00:00:32 | same profile as 604249; no `gpu_metrics.csv` produced |
| 604271 | replay chain (gg, none) | COMPLETED | 00:00:33 | post-summary bugfix validates generated artifact counts (`generated: 4`) |
| 604463 | replay chain (gg, none) | COMPLETED | 00:00:33 | smoke + unpaced full + paced + GPU slot (`CHAIN_GPU_WORKLOAD=none`) |
| 604473 | replay chain (gg, none) | COMPLETED | 00:00:31 | smoke + unpaced full + paced + GPU slot (`CHAIN_GPU_WORKLOAD=none`) |
| 604276 | replay chain (gg, matmul) | FAILED | 00:00:09 | `INPUT_DIR` typo in submit export again |
| 604279 | replay chain (gg, matmul) | FAILED | 00:00:28 | `cupy` missing and `torch` CUDA unavailable |

## March 2 Concrete Chain Results (Replay-Only)
- Completed chain jobs with identical workload pattern: `604244`, `604249`, `604250`, `604271`, `604463`, `604473`.
- Unpaced full run aggregate (800 files, metadata not used):
  - Achieved FPS: min `479.75`, max `537.62`, mean `505.66`.
  - I/O throughput: min `119.94` MiB/s, max `134.41` MiB/s, mean `126.42` MiB/s.
  - p95 frame time: min `2.251 ms`, max `2.628 ms`, mean `2.391 ms`.
- Paced 60 FPS runs met target exactly: all six jobs produced `60.00 FPS`, `15.00 MiB/s`, p95 `~16.668 ms`.
- Smoke control runs (200 files) are control-path only and show non-representative micro-bench performance.

### Reusable Summary for Reporting
- Completed chain jobs + outcomes (replay-only): `604244`, `604249`, `604250`, `604271`, `604463`, `604473` (identical profile).
- Quantified outcomes:
  - Unpaced full mean FPS: `505.66` (range `479.75`–`537.62`).
  - Unpaced full IO: `126.42 MiB/s` mean (range `119.94`–`134.41 MiB/s`).
  - Unpaced full p95 latency: `2.391 ms` mean (range `2.251`–`2.628 ms`).
- Paced 60 FPS behavior: all runs held target exactly (`60.00 FPS`, `15.00 MiB/s`, `~16.668 ms` p95).
- Failure modes logged with causes:
  - `604242`/`604279`: missing CUDA stack (`cupy` missing, `torch` without CUDA).
  - `604243`/`604276`: `INPUT_DIR` typo in submit path export.
- Full raw outputs are linked for exact values in:
  - `docs/chain_metrics_summary.csv`

### Raw Artifacts
- [docs/chain_metrics_summary.csv](/work/11039/logankronforst/vista/tacc-holoscan-replay/docs/chain_metrics_summary.csv)

## Benchmark Results Snapshot
### Bench and Smoke Metrics (selected)
| Job ID | Run Label | Mode | Target FPS | Frames | Duration (s) | Achieved FPS | IO MiB/s |
|---|---|---|---:|---:|---:|---:|---:|
| 602526 | smoke-602526 | metadata | 0 | 200 | 0.000381 | 525299.75 | 131324.94 |
| 602527 | bench-602527 | full | 0 | 800 | 1.255227 | 637.33 | 159.33 |
| 602528 | bench-602528 | full | 30 | 800 | 26.666722 | 30.00 | 7.50 |
| 602529 | bench-602529 | metadata | 60 | 800 | 13.333388 | 60.00 | 15.00 |
| 603086 | bench-603086 | full | 30 | 800 | 26.666723 | 30.00 | 7.50 |
| 603087 | bench-603087 | metadata | 60 | 800 | 13.333386 | 60.00 | 15.00 |
| 603088 | bench-603088 | full | 0 | 800 | 1.542184 | 518.74 | 129.69 |
| 603089 | bench-603089 | full | 30 | 800 | 26.666723 | 30.00 | 7.50 |
| 603090 | bench-603090 | metadata | 0 | 800 | 0.001529 | 523246.23 | 130811.56 |
| 603104 | bench-603104 | metadata | 30 | 200 | 6.666722 | 30.00 | 7.50 |
| 604244 | chain-smoke-604244 | metadata | 0 | 200 | 0.000393 | 508834.75 | 127208.69 |
| 604249 | chain-full-unpaced-604249 | full | 0 | 800 | 1.57 | 515.32 | 128.83 |
| 604250 | chain-full-unpaced-604250 | full | 0 | 800 | 1.58 | 507.37 | 126.84 |
| 604271 | chain-full-unpaced-604271 | full | 0 | 800 | 1.60 | 501.67 | 125.42 |
| 604463 | chain-full-unpaced-604463 | full | 0 | 800 | 1.63 | 492.25 | 123.06 |
| 604473 | chain-full-unpaced-604473 | full | 0 | 800 | 1.49 | 537.62 | 134.41 |

Interpretation notes:
- `metadata` mode unpaced runs are control-path fast paths and are not representative of end-to-end operator compute.
- Paced runs (`TARGET_FPS=30/60`) converge tightly to target rate.

## Timestamp Fidelity Validation
Timestamp validation run:
- Job: `603087`
- Input file: `results/timestamps/ts_800_60hz.csv`
- Timestamp rows: 800
- Result: monotonic `True`, non-monotonic points `0`

Key caveat:
- Runs without `TIMESTAMPS_FILE` store `timestamps: null`; any default `True` in downstream summaries is not proof of timestamp fidelity.

## GPU Efficiency and Telemetry Findings
Telemetry method:
- `nvidia-smi --query-gpu=... --format=csv -lms 500`

Observed behavior:
- Baseline replay runs show sustained `utilization.gpu = 0%` while jobs still complete and produce throughput.
- Synthetic GPU probe (`603104`) shows backend activation (`torch`), `gpu_work_calls=200`, memory rise (~2 MiB to ~676 MiB), and power rise (~90W to ~136W), while sampled `utilization.gpu` still reports `0%`.
- Recent `gg` replay chain runs (`604249`, `604250`, `604271`, `604463`, `604473`) complete with `gpu_monitor_status.txt` containing `nvidia-smi` unavailable, so no telemetry file is produced.
- 604244 (`gh`) also lacked `gpu_metrics.csv`, indicating node-level utility/tooling inconsistency across partitions.

Conclusion from telemetry:
- On this workload/platform, `utilization.gpu [%]` alone is insufficient to infer true GPU activity.
- Efficiency assessment must combine:
  - throughput and frame-time stats,
  - GPU memory and power trends,
  - operator-level timing (recommended next addition).

Mandatory efficiency flags from campaign:
- Under-utilization (<40% sustained util): flagged across baseline runs.
- Over-utilization (near-100% + OOM/tail collapse): not observed.

## Process Constraints and Operational Risks
Hard constraints:
- No live sensor path guarantees on shared environment.
- No claim of live Sensor Bridge parity.
- Queue wait and startup overhead can dominate short jobs.
- Shared filesystem contention can perturb latency tails.
- Queue placement and node mix is unstable; short jobs can sit in `PENDING` for long windows with `Priority/Resources`.
- Node-level GPU observability is inconsistent (`nvidia-smi` may be absent).

Practical implications:
- Always run smoke gate before long chains.
- Prefer compact hypothesis-driven sweeps over broad brute-force grids.
- Track throughput per GPU-hour, not only raw FPS.

## Reproducible Commands
### Full chain submit
```bash
TACC_ALLOC=CCR25007 GPU_PARTITION=gh ./jobs/submit_today.sh
```

### Monitor active chain
```bash
squeue -j <jobids> -o '%i %P %j %t %M %R'
sacct -j <jobids> --format=JobID,State,ExitCode,Elapsed -n
```

### Timestamp validation run
```bash
sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=metadata,MAX_FILES=0,TARGET_FPS=60,TIMESTAMPS_FILE=/work/11039/logankronforst/vista/tacc-holoscan-replay/results/timestamps/ts_800_60hz.csv \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch
```

### Synthetic GPU probe run
```bash
sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=metadata,MAX_FILES=200,TARGET_FPS=30,GPU_WORKLOAD=matmul,GPU_BACKEND=auto,GPU_MAT_SIZE=1024,GPU_ITERS=2,GPU_WORK_EVERY_N=1 \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch
```

## Troubleshooting Notes
- If `python3` module emits load errors:
  - use deterministic module load chain and verify `command -v python3` before execution.
- If GPU telemetry is sparse:
  - increase `GPU_MONITOR_INTERVAL_MS` sampling density and prefer longer runs for analysis.
- If `sbatch --parsable` output includes non-numeric text:
  - sanitize/parsing logic must extract trailing numeric job id only.
- If no replay files found:
  - validate `INPUT_DIR`, `glob`, and extension filters.

## Source File Index
- Entrypoint: `src/replay_entrypoint.py`
- Aggregation: `src/aggregate_results.py`
- Submit helper: `jobs/submit_today.sh`
- Jobs:
  - `jobs/replay_smoke.sbatch`
  - `jobs/replay_benchmark.sbatch`
  - `jobs/replay_sweep.sbatch`
  - `jobs/aggregate_report.sbatch`
- Analysis inputs:
  - `docs/chain_metrics_summary.csv`
- Supporting analysis doc: `docs/limits-and-observed-performance.md`

## Final Technical Status
Current status as of March 2, 2026:
- Replay workflow and reporting pipeline are stable and reproducible on Vista.
- Timestamp-file handling is explicitly validated.
- Synthetic GPU workload path is implemented; execution is currently blocked on current nodes by missing CUDA (`cupy` absent, `torch` no CUDA).
- Live Sensor Bridge parity remains out of scope and unclaimed.
- Latest completed replay-only chain set is in `results/chain/{604244,604249,604250,604271,604463,604473}`; no GPU telemetry captured on those host sets (`nvidia-smi unavailable`).
