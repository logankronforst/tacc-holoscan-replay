#!/bin/bash
#SBATCH -J hs_replay_chain
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 02:00:00

set -euo pipefail

REPO_DIR="${REPO_DIR:-$SLURM_SUBMIT_DIR}"
INPUT_DIR="${INPUT_DIR:-/scratch/11039/logankronforst/replay_data}"
OUT_DIR="${OUT_DIR:-$REPO_DIR/results/chain/${SLURM_JOB_ID}}"
CHAIN_GPU_WORKLOAD="${CHAIN_GPU_WORKLOAD:-none}"
CHAIN_GPU_BACKEND="${CHAIN_GPU_BACKEND:-auto}"
CHAIN_GPU_MAT_SIZE="${CHAIN_GPU_MAT_SIZE:-256}"
CHAIN_GPU_ITERS="${CHAIN_GPU_ITERS:-2}"
CHAIN_GPU_WORK_EVERY_N="${CHAIN_GPU_WORK_EVERY_N:-1}"
GPU_MONITOR_INTERVAL_MS="${GPU_MONITOR_INTERVAL_MS:-500}"
mkdir -p "$OUT_DIR/smoke" "$OUT_DIR/bench_full" "$OUT_DIR/bench_paced" "$OUT_DIR/bench_gpu"
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
  sleep 1
  if ! kill -0 "${GPU_MON_PID}" >/dev/null 2>&1; then
    echo "nvidia-smi exited before workload start" > "$OUT_DIR/gpu_monitor_status.txt"
    GPU_MON_PID=""
  fi
else
  echo "nvidia-smi unavailable in runtime environment" > "$OUT_DIR/gpu_monitor_status.txt"
fi
cleanup() {
  if [[ -n "${GPU_MON_PID}" ]] && kill -0 "${GPU_MON_PID}" >/dev/null 2>&1; then
    kill "${GPU_MON_PID}" || true
  fi
}
trap cleanup EXIT

python3 src/replay_entrypoint.py \
  --input-dir "$INPUT_DIR" \
  --glob "**/*" \
  --max-files 200 \
  --read-mode metadata \
  --output-json "$OUT_DIR/smoke/metrics.json" \
  --run-label "chain-smoke-${SLURM_JOB_ID}"

python3 src/replay_entrypoint.py \
  --input-dir "$INPUT_DIR" \
  --glob "**/*" \
  --max-files 800 \
  --read-mode full \
  --target-fps 0 \
  --output-json "$OUT_DIR/bench_full/full_unpaced.json" \
  --run-label "chain-full-unpaced-${SLURM_JOB_ID}"

python3 src/replay_entrypoint.py \
  --input-dir "$INPUT_DIR" \
  --glob "**/*" \
  --max-files 800 \
  --read-mode full \
  --target-fps 60 \
  --output-json "$OUT_DIR/bench_paced/full_60fps.json" \
  --run-label "chain-full-60fps-${SLURM_JOB_ID}"

python3 src/replay_entrypoint.py \
  --input-dir "$INPUT_DIR" \
  --glob "**/*" \
  --max-files 200 \
  --read-mode metadata \
  --target-fps 30 \
  --gpu-workload "$CHAIN_GPU_WORKLOAD" \
  --gpu-backend "$CHAIN_GPU_BACKEND" \
  --gpu-mat-size "$CHAIN_GPU_MAT_SIZE" \
  --gpu-iters "$CHAIN_GPU_ITERS" \
  --gpu-work-every-n "$CHAIN_GPU_WORK_EVERY_N" \
  --output-json "$OUT_DIR/bench_gpu/gpu_matmul.json" \
  --run-label "chain-gpu-matmul-${SLURM_JOB_ID}"

python3 - <<PY
import json
from pathlib import Path
root = Path("$OUT_DIR")
files = sorted(root.rglob('*.json'))
print('generated:', len(files))
for p in files:
    d = json.loads(p.read_text())
    m = d.get('metrics', {})
    print(p.name, m.get('frames'), m.get('achieved_fps'), m.get('io_mib_per_sec'), m.get('frame_time_ms', {}).get('p95'))
PY
