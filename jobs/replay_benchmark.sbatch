#!/bin/bash
#SBATCH -J hs_replay_bench
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 01:00:00
# Vista gh partitions reject --gres=gpu; resource policy is partition-defined.
# SBATCH -A <YOUR_TACC_ALLOCATION>
# SBATCH -p <GPU_PARTITION>

set -euo pipefail

REPO_DIR="${REPO_DIR:-$SLURM_SUBMIT_DIR}"
INPUT_DIR="${INPUT_DIR:-$SCRATCH/replay_data}"
OUT_DIR="${OUT_DIR:-$REPO_DIR/results/bench/${SLURM_JOB_ID}}"
GLOB_PATTERN="${GLOB_PATTERN:-**/*}"
MAX_FILES="${MAX_FILES:-0}"
TARGET_FPS="${TARGET_FPS:-0}"
SLEEP_OP_MS="${SLEEP_OP_MS:-0}"
READ_MODE="${READ_MODE:-full}"
TIMESTAMPS_FILE="${TIMESTAMPS_FILE:-}"
GPU_WORKLOAD="${GPU_WORKLOAD:-none}"
GPU_BACKEND="${GPU_BACKEND:-auto}"
GPU_MAT_SIZE="${GPU_MAT_SIZE:-1024}"
GPU_ITERS="${GPU_ITERS:-2}"
GPU_WORK_EVERY_N="${GPU_WORK_EVERY_N:-1}"
GPU_MONITOR_INTERVAL_MS="${GPU_MONITOR_INTERVAL_MS:-500}"

mkdir -p "$REPO_DIR/logs" "$OUT_DIR"
cd "$REPO_DIR"

module purge
if ! module load gcc/13.2.0 python3 >/dev/null 2>&1; then
  module load python3 >/dev/null 2>&1 || true
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 unavailable after module setup" >&2
  exit 3
fi

GPU_MON_PID=""
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -lms "$GPU_MONITOR_INTERVAL_MS" > "$OUT_DIR/gpu_metrics.csv" &
  GPU_MON_PID="$!"
fi
cleanup() {
  if [[ -n "${GPU_MON_PID}" ]] && kill -0 "${GPU_MON_PID}" >/dev/null 2>&1; then
    kill "${GPU_MON_PID}" || true
  fi
}
trap cleanup EXIT

CMD=(
  python3 src/replay_entrypoint.py
  --input-dir "$INPUT_DIR"
  --glob "$GLOB_PATTERN"
  --max-files "$MAX_FILES"
  --read-mode "$READ_MODE"
  --target-fps "$TARGET_FPS"
  --sleep-operator-ms "$SLEEP_OP_MS"
  --gpu-workload "$GPU_WORKLOAD"
  --gpu-backend "$GPU_BACKEND"
  --gpu-mat-size "$GPU_MAT_SIZE"
  --gpu-iters "$GPU_ITERS"
  --gpu-work-every-n "$GPU_WORK_EVERY_N"
  --output-json "$OUT_DIR/metrics.json"
  --run-label "bench-${SLURM_JOB_ID}"
)

if [[ -n "$TIMESTAMPS_FILE" ]]; then
  CMD+=(--timestamps-file "$TIMESTAMPS_FILE")
fi

"${CMD[@]}"

echo "Benchmark replay complete: $OUT_DIR/metrics.json"
