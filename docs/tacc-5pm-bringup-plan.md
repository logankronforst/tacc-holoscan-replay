# TACC Replay Bring-Up Plan (Today by 5pm)

## Mission
Get replay-mode execution running, collect benchmark numbers, and publish constraints.

## Mandatory Limitation Statement
Do not claim live Sensor Bridge parity unless dedicated provisioning is confirmed.

## 0) Preflight (15-30 min)
1. Confirm TACC allocation, GPU queue/partition, and walltime.
2. Stage replay data under `$SCRATCH/replay_data`.
3. Ensure Python is available (`module load python3`).

## 1) Smoke Run (30 min)
1. Edit `jobs/replay_smoke.sbatch` account/partition lines.
2. Submit:
   - `sbatch -A <alloc> -p <gpu_partition> jobs/replay_smoke.sbatch`
3. Check output JSON under `results/smoke/<job_id>/metrics.json`.

Pass criteria:
- Input files discovered.
- Non-zero frame count.
- Job exits successfully.

## 2) Main Benchmark Run (60-90 min)
1. Submit with full reads:
   - `sbatch -A <alloc> -p <gpu_partition> --export=ALL,READ_MODE=full,MAX_FILES=0,TARGET_FPS=0 jobs/replay_benchmark.sbatch`
2. Optional timestamp validation:
   - add `TIMESTAMPS_FILE=/path/to/timestamps.csv`
3. Repeat 3 times for variance.

Collect from each run:
- `achieved_fps`
- `io_mib_per_sec`
- frame-time `p50/p95/p99`
- timestamp monotonic check (if provided)
- GPU utilization and memory telemetry from `gpu_metrics.csv`

## 3) Parameter Sweep (60-120 min)
1. Submit sweep:
   - `sbatch -A <alloc> -p <gpu_partition> --export=ALL,FPS_LIST='0 30 60',READ_MODES='metadata full' jobs/replay_sweep.sbatch`
2. Aggregate JSON outputs in `results/sweep/<job_id>/`.

## 4) Publish Results (30 min)
1. Fill `docs/limits-and-observed-performance.md`.
2. Include deviations from live hardware behavior.
3. State clearly: replay validated, live sensor path not validated.
4. Aggregate sweep JSON files:
   - `python3 src/aggregate_results.py --input-dir results/sweep/<job_id> --output-csv results/sweep/<job_id>/summary.csv --output-md results/sweep/<job_id>/summary.md`

## Same-Day Minimum Deliverable
- One successful smoke run.
- Three benchmark runs with summary table.
- One explicit limitations report.
