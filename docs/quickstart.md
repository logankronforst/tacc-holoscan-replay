# Quickstart

## Local Sanity Check
1. Create a tiny dataset directory with files.
2. Run:
   - `python3 src/replay_entrypoint.py --input-dir <data_dir> --output-json /tmp/metrics.json`
3. Confirm `/tmp/metrics.json` exists and has non-zero frames.

## TACC Smoke Submit
- `sbatch -A <alloc> -p <gpu_partition> jobs/replay_smoke.sbatch`

## TACC Benchmark Submit
- `sbatch -A <alloc> -p <gpu_partition> jobs/replay_benchmark.sbatch`

## TACC Sweep Submit
- `sbatch -A <alloc> -p <gpu_partition> jobs/replay_sweep.sbatch`

## Chained Submit
- `TACC_ALLOC=<alloc> GPU_PARTITION=<gpu_partition> ./jobs/submit_today.sh`

## Aggregate Results
- `python3 src/aggregate_results.py --input-dir results/sweep/<job_id> --output-csv results/sweep/<job_id>/summary.csv --output-md results/sweep/<job_id>/summary.md`
