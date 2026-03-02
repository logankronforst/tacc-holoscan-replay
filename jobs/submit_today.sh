#!/bin/bash
set -euo pipefail

# Usage:
#   TACC_ALLOC=<alloc> GPU_PARTITION=<partition> ./jobs/submit_today.sh

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOC="${TACC_ALLOC:-}"
PARTITION="${GPU_PARTITION:-}"
INPUT_DIR="${INPUT_DIR:-$SCRATCH/replay_data}"

if [[ -z "$ALLOC" || -z "$PARTITION" ]]; then
  echo "ERROR: set TACC_ALLOC and GPU_PARTITION"
  exit 1
fi

if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: sbatch not found in PATH"
  exit 2
fi

mkdir -p "$REPO_DIR/logs"

echo "Submitting smoke run..."
SMOKE_JOB=$(sbatch --parsable -A "$ALLOC" -p "$PARTITION" --export=ALL,INPUT_DIR="$INPUT_DIR" "$REPO_DIR/jobs/replay_smoke.sbatch" | tail -n 1 | tr -dc '0-9')
echo "Smoke job id: $SMOKE_JOB"

echo "Submitting 3 benchmark runs after smoke..."
BENCH1=$(sbatch --parsable -A "$ALLOC" -p "$PARTITION" --dependency=afterok:$SMOKE_JOB --export=ALL,INPUT_DIR="$INPUT_DIR",READ_MODE=full,MAX_FILES=0,TARGET_FPS=0 "$REPO_DIR/jobs/replay_benchmark.sbatch" | tail -n 1 | tr -dc '0-9')
BENCH2=$(sbatch --parsable -A "$ALLOC" -p "$PARTITION" --dependency=afterok:$SMOKE_JOB --export=ALL,INPUT_DIR="$INPUT_DIR",READ_MODE=full,MAX_FILES=0,TARGET_FPS=30 "$REPO_DIR/jobs/replay_benchmark.sbatch" | tail -n 1 | tr -dc '0-9')
BENCH3=$(sbatch --parsable -A "$ALLOC" -p "$PARTITION" --dependency=afterok:$SMOKE_JOB --export=ALL,INPUT_DIR="$INPUT_DIR",READ_MODE=metadata,MAX_FILES=0,TARGET_FPS=60 "$REPO_DIR/jobs/replay_benchmark.sbatch" | tail -n 1 | tr -dc '0-9')

echo "Benchmark job ids: $BENCH1 $BENCH2 $BENCH3"

echo "Submitting sweep run after all benchmark runs..."
SWEEP_JOB=$(sbatch --parsable -A "$ALLOC" -p "$PARTITION" --dependency=afterok:$BENCH1:$BENCH2:$BENCH3 --export=ALL,INPUT_DIR="$INPUT_DIR",FPS_LIST='0 30 60',READ_MODES='metadata full' "$REPO_DIR/jobs/replay_sweep.sbatch" | tail -n 1 | tr -dc '0-9')
echo "Sweep job id: $SWEEP_JOB"

echo "Done. Monitor with: squeue -u $USER"
