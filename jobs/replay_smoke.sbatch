#!/bin/bash
#SBATCH -J hs_replay_smoke
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 00:15:00
# Vista gh partitions reject --gres=gpu; resource policy is partition-defined.
# SBATCH -A <YOUR_TACC_ALLOCATION>
# SBATCH -p <GPU_PARTITION>

set -euo pipefail

REPO_DIR="${REPO_DIR:-$SLURM_SUBMIT_DIR}"
INPUT_DIR="${INPUT_DIR:-$SCRATCH/replay_data}"
OUT_DIR="${OUT_DIR:-$REPO_DIR/results/smoke/${SLURM_JOB_ID}}"
GLOB_PATTERN="${GLOB_PATTERN:-**/*}"
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

python3 src/replay_entrypoint.py \
  --input-dir "$INPUT_DIR" \
  --glob "$GLOB_PATTERN" \
  --max-files 200 \
  --read-mode metadata \
  --output-json "$OUT_DIR/metrics.json" \
  --run-label "smoke-${SLURM_JOB_ID}"

echo "Smoke replay complete: $OUT_DIR/metrics.json"
