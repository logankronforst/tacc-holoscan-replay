# Replay Limits and Observed Performance

## Scope Statement
This document reports replay-mode Holoscan validation on shared TACC Vista GPU resources.

Replay validated. Live sensor path validated: no.

## Mandatory Limitation Statement
Do not claim live Sensor Bridge parity unless dedicated provisioning is confirmed.

## Environment
- Date of observed runs: March 1, 2026 (UTC-6 local scheduler time)
- Cluster/system: TACC Vista
- Queue/partition: `gh`
- Account: `CCR25007`
- GPU type/count: 1x NVIDIA GH200 120GB per job (from `nvidia-smi` telemetry)
- Replay input path: `/scratch/11039/logankronforst/replay_data`
- Runtime: `module load gcc/13.2.0 python3` (with fallback and hard `python3` availability check)
- GPU telemetry sampling: `nvidia-smi ... -lms 500` (500 ms interval)

## Replay Input Fidelity
- File discovery + read checks: replay harness scans `**/*` under input dir and processes all matching files.
- Dataset observed in these jobs: 800 frames for benchmark/sweep runs; 200 frames for smoke runs.
- Byte volume observed: 209,715,200 bytes for 800-frame benchmark runs.
- Timestamp source and format (explicit validation run): `results/timestamps/ts_800_60hz.csv`, CSV header `timestamp`, 800 values at ~60 Hz spacing.
- Timestamp monotonic result: `True` for benchmark job `603087`.
- Timestamp count: 800 for `603087`; `0` (null timestamps) in previous runs without `TIMESTAMPS_FILE`.
- Non-monotonic points: `0` for `603087`.

## Operator and Pipeline Validation
- Pipeline entrypoint: `src/replay_entrypoint.py`
- Aggregation entrypoint: `src/aggregate_results.py`
- Successful chain observed:
  - Smoke: `602526`
  - Bench: `602527`, `602528`, `602529`
  - Sweep: `602530`
  - Aggregate: `602532`
- Additional validation jobs:
  - Timestamp fidelity: `603087`
  - Efficiency probe: `603088`, `603089`, `603090`
- Expected outputs and observed outputs:
  - Bench jobs produced `results/bench/<jobid>/metrics.json` and `gpu_metrics.csv`.
  - Sweep job produced six per-mode JSONs plus `summary.csv` and `summary.md`.
  - Aggregate job produced/updated `summary.csv` and `summary.md`.
- Completion status: all listed jobs `COMPLETED` with `ExitCode 0:0`.
- Failures/retries: none observed in Slurm accounting for listed jobs.

## Observed Performance
| Job ID | Run label | Mode | Target FPS | Frames | Duration (s) | Achieved FPS | IO MiB/s | p95 ms | Timestamp count | Timestamp monotonic |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 603087 | bench-603087 | metadata | 60 | 800 | 13.333386 | 60.00 | 15.00 | 16.6670 | 800 | True |
| 603088 | bench-603088 | full | 0 | 800 | 1.542184 | 518.74 | 129.69 | 2.2971 | 0 | True* |
| 603089 | bench-603089 | full | 30 | 800 | 26.666723 | 30.00 | 7.50 | 33.3336 | 0 | True* |
| 603090 | bench-603090 | metadata | 0 | 800 | 0.001529 | 523246.23 | 130811.56 | 0.0020 | 0 | True* |

\*`True` here is default behavior when no timestamp file is provided; it is not a fidelity assertion.

## GPU Utilization Efficiency
- Telemetry files:
  - `results/bench/603087/gpu_metrics.csv`
  - `results/bench/603088/gpu_metrics.csv`
  - `results/bench/603089/gpu_metrics.csv`
  - `results/bench/603090/gpu_metrics.csv`
- Per-run efficiency signals:
  - `603087`: 28 samples, mean util 0.00%, p95 util 0.00%, mean mem 0.25 MiB, peak mem 1 MiB, mean power 91.24 W.
  - `603088`: 4 samples, mean util 0.00%, p95 util 0.00%, mean mem 2.00 MiB, peak mem 2 MiB, mean power 72.56 W.
  - `603089`: 54 samples, mean util 0.00%, p95 util 0.00%, mean mem 0.76 MiB, peak mem 1 MiB, mean power 91.21 W.
  - `603090`: 1 sample, mean util 0.00%, p95 util 0.00%, mean mem 2.00 MiB, peak mem 2 MiB, mean power 72.87 W.
- Throughput per GPU-hour (frames / GPU-hour):
  - `603087`: 215,999
  - `603088`: 1,867,482
  - `603089`: 107,999
  - `603090`: 1,883,686,443 (metadata-only fast path; not representative of end-to-end GPU compute)
- Under-utilization flag (mandatory criterion): yes, sustained `<40%` utilization in all observed runs.
- Over-utilization flag: no (no near-100% sustained utilization, no OOM, no retries).
- Documented wasted/idle GPU causes:
  - Current replay harness is primarily file/metadata processing and pacing logic, with no substantial GPU kernel workload.
  - Very short unpaced metadata runs complete too quickly for meaningful GPU activity windows.
  - Queue/startup overhead dominates total walltime for short jobs.

## Synthetic GPU Operator Probe
- Probe job: `603104` (`READ_MODE=metadata`, `TARGET_FPS=30`, `MAX_FILES=200`, `GPU_WORKLOAD=matmul`, `GPU_BACKEND=auto`).
- Result: `COMPLETED (0:0)` and selected backend in metrics was `torch` (`gpu_work_info.backend=torch`).
- Synthetic GPU calls: `gpu_work_calls=200` (one call per frame).
- Observed effect:
  - GPU memory used rose from ~2 MiB baseline to ~676 MiB during workload window.
  - Power draw rose from ~90 W baseline to ~136 W during workload window.
  - `utilization.gpu [%]` remained `0%` in sampled `nvidia-smi` output on GH200 despite memory/power change.
- Interpretation:
  - Synthetic GPU path is active and allocated device memory/work.
  - On this platform/telemetry mode, utilization percentage alone may under-report activity; include memory/power and operator timing when judging efficiency.

## Deviations from Live Hardware Behavior
1. Replay timing does not validate live Sensor Bridge transport or ingest behavior.
2. No dedicated provisioning confirmation for live-path parity.
3. Timestamp checks validate file-provided sequences, not hardware clock synchronization (PTP/live capture timing).
4. Shared filesystem and scheduler jitter can affect tails compared with dedicated live deployments.

## Repro Commands (Observed)
```bash
# Timestamp validation benchmark
sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=metadata,MAX_FILES=0,TARGET_FPS=60,TIMESTAMPS_FILE=/work/11039/logankronforst/vista/tacc-holoscan-replay/results/timestamps/ts_800_60hz.csv \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch

# Efficiency probe set
sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=full,MAX_FILES=0,TARGET_FPS=0 \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch

sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=full,MAX_FILES=0,TARGET_FPS=30 \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch

sbatch --parsable -A CCR25007 -p gh \
  --export=ALL,INPUT_DIR=/scratch/11039/logankronforst/replay_data,READ_MODE=metadata,MAX_FILES=0,TARGET_FPS=0 \
  /work/11039/logankronforst/vista/tacc-holoscan-replay/jobs/replay_benchmark.sbatch
```

## Conclusion
- Validated:
  - Replay-mode execution, completion, and artifact generation on Vista.
  - Timestamp monotonicity/count when explicit timestamp input is provided.
  - Aggregation workflow generation of CSV/Markdown summaries.
- Not validated:
  - Live Sensor Bridge parity, live ingest equivalence, or hardware clock synchronization behavior.
  - Any sustained GPU-heavy execution path in current harness.
- Next requirements for live-path validation:
  - Integrate and exercise GPU-backed operators representative of target Holoscan graph.
  - Re-run efficiency sweeps with true GPU workload and track throughput per GPU-hour.
  - Validate live ingest path with dedicated provisioning before parity claims.
