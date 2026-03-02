#!/usr/bin/env python3
"""Replay benchmark entrypoint for TACC-friendly Holoscan validation.

This script provides a reproducible replay benchmark harness even before full
Holoscan graph integration is available on the target cluster.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


@dataclass
class TimestampStats:
    count: int
    monotonic: bool
    non_monotonic_points: int
    min_delta_ms: float | None
    max_delta_ms: float | None
    mean_delta_ms: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay benchmark harness")
    parser.add_argument("--input-dir", required=True, help="Directory containing replay files")
    parser.add_argument(
        "--glob",
        default="**/*",
        help="Glob pattern relative to --input-dir (default: **/*)",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[".bin", ".dat", ".raw", ".jpg", ".jpeg", ".png", ".npy", ".json"],
        help="Optional extension allowlist; use --extensions '*' to disable filtering",
    )
    parser.add_argument("--max-files", type=int, default=0, help="0 means all files")
    parser.add_argument(
        "--read-mode",
        choices=["metadata", "full"],
        default="metadata",
        help="metadata=stat only, full=read full file bytes",
    )
    parser.add_argument("--target-fps", type=float, default=0.0, help="0 means no pacing")
    parser.add_argument("--sleep-operator-ms", type=float, default=0.0, help="Synthetic operator latency")
    parser.add_argument(
        "--gpu-workload",
        choices=["none", "matmul"],
        default="none",
        help="Optional synthetic GPU operator workload",
    )
    parser.add_argument(
        "--gpu-backend",
        choices=["auto", "cupy", "torch"],
        default="auto",
        help="GPU backend for synthetic workload",
    )
    parser.add_argument("--gpu-mat-size", type=int, default=1024, help="Square matrix size for matmul workload")
    parser.add_argument("--gpu-iters", type=int, default=2, help="Matmul iterations per synthetic operator call")
    parser.add_argument(
        "--gpu-work-every-n",
        type=int,
        default=1,
        help="Run synthetic GPU workload every N frames (default: 1)",
    )
    parser.add_argument("--timestamps-file", default="", help="Optional txt/csv/jsonl file with timestamps")
    parser.add_argument("--timestamp-column", default="timestamp", help="Timestamp column for csv/jsonl")
    parser.add_argument("--output-json", required=True, help="Metrics output path")
    parser.add_argument("--run-label", default="replay-benchmark")
    return parser.parse_args()


def percentile(sorted_values: Sequence[float], p: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return sorted_values[lo]
    frac = rank - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def discover_files(input_dir: Path, pattern: str, extensions: list[str], max_files: int) -> list[Path]:
    all_paths = [p for p in input_dir.glob(pattern) if p.is_file()]
    all_paths.sort()

    if extensions != ["*"]:
        lowered = {ext.lower() for ext in extensions}
        all_paths = [p for p in all_paths if p.suffix.lower() in lowered]

    if max_files > 0:
        all_paths = all_paths[:max_files]
    return all_paths


def load_timestamps(path: Path, column: str) -> list[float]:
    if not path.exists():
        raise FileNotFoundError(f"timestamps file not found: {path}")

    suffix = path.suffix.lower()
    timestamps: list[float] = []

    if suffix in {".txt", ".log"}:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                timestamps.append(float(line.split()[0]))
        return timestamps

    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or column not in reader.fieldnames:
                raise ValueError(f"csv missing column '{column}'")
            for row in reader:
                timestamps.append(float(row[column]))
        return timestamps

    if suffix in {".json", ".jsonl"}:
        with path.open("r", encoding="utf-8") as f:
            if suffix == ".json":
                payload = json.load(f)
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict):
                            timestamps.append(float(item[column]))
                        else:
                            timestamps.append(float(item))
                else:
                    raise ValueError("json timestamps file must contain a list")
            else:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    if isinstance(item, dict):
                        timestamps.append(float(item[column]))
                    else:
                        timestamps.append(float(item))
        return timestamps

    raise ValueError("timestamps file must be txt/csv/json/jsonl")


def summarize_timestamps(values: Iterable[float]) -> TimestampStats:
    ts = list(values)
    if len(ts) < 2:
        return TimestampStats(
            count=len(ts),
            monotonic=True,
            non_monotonic_points=0,
            min_delta_ms=None,
            max_delta_ms=None,
            mean_delta_ms=None,
        )

    deltas_ms = []
    non_monotonic = 0
    prev = ts[0]
    for cur in ts[1:]:
        delta = cur - prev
        if delta < 0:
            non_monotonic += 1
        deltas_ms.append(delta * 1000.0)
        prev = cur

    return TimestampStats(
        count=len(ts),
        monotonic=(non_monotonic == 0),
        non_monotonic_points=non_monotonic,
        min_delta_ms=min(deltas_ms),
        max_delta_ms=max(deltas_ms),
        mean_delta_ms=statistics.mean(deltas_ms),
    )


def init_gpu_worker(
    workload: str,
    backend: str,
    mat_size: int,
    iters: int,
) -> tuple[Callable[[], None] | None, dict[str, Any]]:
    if workload == "none":
        return None, {"enabled": False, "workload": "none", "backend": None}

    if mat_size <= 0:
        raise ValueError("--gpu-mat-size must be > 0")
    if iters <= 0:
        raise ValueError("--gpu-iters must be > 0")

    backends = ["cupy", "torch"] if backend == "auto" else [backend]
    errors: list[str] = []

    if "cupy" in backends:
        try:
            import cupy as cp  # type: ignore

            a = cp.random.random((mat_size, mat_size), dtype=cp.float32)
            b = cp.random.random((mat_size, mat_size), dtype=cp.float32)

            def run_cupy() -> None:
                out = a
                for _ in range(iters):
                    out = out @ b
                cp.cuda.runtime.deviceSynchronize()

            return (
                run_cupy,
                {
                    "enabled": True,
                    "workload": workload,
                    "backend": "cupy",
                    "matrix_size": mat_size,
                    "iters_per_call": iters,
                },
            )
        except Exception as exc:  # pragma: no cover
            errors.append(f"cupy: {exc}")

    if "torch" in backends:
        try:
            import torch  # type: ignore

            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available in torch")
            device = torch.device("cuda")
            a = torch.rand((mat_size, mat_size), device=device, dtype=torch.float32)
            b = torch.rand((mat_size, mat_size), device=device, dtype=torch.float32)

            def run_torch() -> None:
                out = a
                for _ in range(iters):
                    out = out @ b
                torch.cuda.synchronize()

            return (
                run_torch,
                {
                    "enabled": True,
                    "workload": workload,
                    "backend": "torch",
                    "matrix_size": mat_size,
                    "iters_per_call": iters,
                },
            )
        except Exception as exc:  # pragma: no cover
            errors.append(f"torch: {exc}")

    raise RuntimeError(
        "failed to initialize synthetic GPU workload backend; "
        f"requested backend={backend}, errors={' | '.join(errors) if errors else 'none'}"
    )


def benchmark(
    files: list[Path],
    read_mode: str,
    target_fps: float,
    sleep_operator_ms: float,
    gpu_worker: Callable[[], None] | None,
    gpu_work_every_n: int,
) -> dict:
    frame_times_ms = []
    total_bytes = 0
    gpu_calls = 0

    run_start = time.perf_counter()
    next_deadline = run_start

    for idx, path in enumerate(files):
        frame_start = time.perf_counter()

        if read_mode == "metadata":
            total_bytes += path.stat().st_size
        else:
            total_bytes += len(path.read_bytes())

        if gpu_worker is not None and gpu_work_every_n > 0 and idx % gpu_work_every_n == 0:
            gpu_worker()
            gpu_calls += 1

        if sleep_operator_ms > 0:
            time.sleep(sleep_operator_ms / 1000.0)

        if target_fps > 0:
            frame_period = 1.0 / target_fps
            next_deadline = run_start + (idx + 1) * frame_period
            now = time.perf_counter()
            if next_deadline > now:
                time.sleep(next_deadline - now)

        frame_end = time.perf_counter()
        frame_times_ms.append((frame_end - frame_start) * 1000.0)

    run_end = time.perf_counter()
    duration_sec = max(run_end - run_start, 1e-9)

    sorted_frames = sorted(frame_times_ms)
    achieved_fps = len(files) / duration_sec if files else 0.0
    io_mib_s = (total_bytes / (1024 * 1024)) / duration_sec

    return {
        "frames": len(files),
        "duration_sec": duration_sec,
        "achieved_fps": achieved_fps,
        "io_mib_per_sec": io_mib_s,
        "total_bytes": total_bytes,
        "gpu_work_calls": gpu_calls,
        "frame_time_ms": {
            "p50": percentile(sorted_frames, 50),
            "p95": percentile(sorted_frames, 95),
            "p99": percentile(sorted_frames, 99),
            "max": max(sorted_frames) if sorted_frames else math.nan,
        },
    }


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"input dir not found: {input_dir}")

    files = discover_files(input_dir, args.glob, args.extensions, args.max_files)
    if not files:
        raise RuntimeError("no replay files found for selected glob/extensions")

    ts_summary = None
    if args.timestamps_file:
        ts_values = load_timestamps(Path(args.timestamps_file).expanduser().resolve(), args.timestamp_column)
        ts_summary = summarize_timestamps(ts_values)

    if args.gpu_work_every_n <= 0:
        raise ValueError("--gpu-work-every-n must be > 0")

    gpu_worker, gpu_work_info = init_gpu_worker(
        workload=args.gpu_workload,
        backend=args.gpu_backend,
        mat_size=args.gpu_mat_size,
        iters=args.gpu_iters,
    )

    metrics = benchmark(
        files=files,
        read_mode=args.read_mode,
        target_fps=args.target_fps,
        sleep_operator_ms=args.sleep_operator_ms,
        gpu_worker=gpu_worker,
        gpu_work_every_n=args.gpu_work_every_n,
    )

    payload = {
        "run_label": args.run_label,
        "input_dir": str(input_dir),
        "glob": args.glob,
        "extensions": args.extensions,
        "max_files": args.max_files,
        "read_mode": args.read_mode,
        "target_fps": args.target_fps,
        "sleep_operator_ms": args.sleep_operator_ms,
        "gpu_workload": args.gpu_workload,
        "gpu_backend": args.gpu_backend,
        "gpu_mat_size": args.gpu_mat_size,
        "gpu_iters": args.gpu_iters,
        "gpu_work_every_n": args.gpu_work_every_n,
        "gpu_work_info": gpu_work_info,
        "metrics": metrics,
        "timestamps": (ts_summary.__dict__ if ts_summary else None),
        "notes": [
            "Replay validated scope only.",
            "No claim of live Sensor Bridge parity without dedicated provisioning.",
        ],
        "generated_at_epoch_sec": time.time(),
    }

    output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote metrics: {output_json}")
    print(f"frames={metrics['frames']} achieved_fps={metrics['achieved_fps']:.2f} io_mib_s={metrics['io_mib_per_sec']:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
