#!/bin/bash
#SBATCH -J hs_replay_agg
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 00:10:00

set -euo pipefail

REPO_DIR="${REPO_DIR:-$SLURM_SUBMIT_DIR}"
SWEEP_JOB_ID="${SWEEP_JOB_ID:?SWEEP_JOB_ID required}"
SWEEP_DIR="${SWEEP_DIR:-$REPO_DIR/results/sweep/${SWEEP_JOB_ID}}"
OUT_CSV="${OUT_CSV:-$SWEEP_DIR/summary.csv}"
OUT_MD="${OUT_MD:-$SWEEP_DIR/summary.md}"

mkdir -p "$REPO_DIR/logs"
cd "$REPO_DIR"

module purge
if ! module load gcc/13.2.0 python3 >/dev/null 2>&1; then
  module load python3 >/dev/null 2>&1 || true
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 unavailable after module setup" >&2
  exit 3
fi

python3 src/aggregate_results.py \
  --input-dir "$SWEEP_DIR" \
  --glob '*.json' \
  --output-csv "$OUT_CSV" \
  --output-md "$OUT_MD"

echo "Aggregation complete: $OUT_CSV and $OUT_MD"
