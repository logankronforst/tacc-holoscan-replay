#!/usr/bin/env python3
"""Aggregate replay benchmark JSON outputs into CSV and Markdown summaries."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate replay benchmark JSON outputs")
    p.add_argument("--input-dir", required=True, help="Directory containing *.json benchmark files")
    p.add_argument("--glob", default="*.json", help="Glob to select JSON files")
    p.add_argument("--output-csv", required=True, help="Per-run CSV output path")
    p.add_argument("--output-md", required=True, help="Markdown summary output path")
    return p.parse_args()


def _safe_float(v: Any) -> float:
    try:
        out = float(v)
    except Exception:
        return math.nan
    return out


def load_rows(input_dir: Path, pattern: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob(pattern)):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics = payload.get("metrics", {})
        ft = metrics.get("frame_time_ms", {})
        ts = payload.get("timestamps") or {}

        row = {
            "file": str(path),
            "run_label": payload.get("run_label", path.stem),
            "read_mode": payload.get("read_mode", ""),
            "target_fps": _safe_float(payload.get("target_fps", math.nan)),
            "frames": int(metrics.get("frames", 0) or 0),
            "duration_sec": _safe_float(metrics.get("duration_sec", math.nan)),
            "achieved_fps": _safe_float(metrics.get("achieved_fps", math.nan)),
            "io_mib_per_sec": _safe_float(metrics.get("io_mib_per_sec", math.nan)),
            "p50_ms": _safe_float(ft.get("p50", math.nan)),
            "p95_ms": _safe_float(ft.get("p95", math.nan)),
            "p99_ms": _safe_float(ft.get("p99", math.nan)),
            "timestamp_count": int(ts.get("count", 0) or 0),
            "timestamp_monotonic": bool(ts.get("monotonic", True)),
            "timestamp_non_monotonic_points": int(ts.get("non_monotonic_points", 0) or 0),
        }
        rows.append(row)
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "file",
        "run_label",
        "read_mode",
        "target_fps",
        "frames",
        "duration_sec",
        "achieved_fps",
        "io_mib_per_sec",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "timestamp_count",
        "timestamp_monotonic",
        "timestamp_non_monotonic_points",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _mean(xs: list[float]) -> float:
    vals = [x for x in xs if not math.isnan(x)]
    return statistics.mean(vals) if vals else math.nan


def _stdev(xs: list[float]) -> float:
    vals = [x for x in xs if not math.isnan(x)]
    return statistics.pstdev(vals) if vals else math.nan


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = (row["read_mode"], str(row["target_fps"]), row["target_fps"])
        grouped[key].append(row)

    lines: list[str] = []
    lines.append("# Replay Benchmark Summary")
    lines.append("")
    lines.append("## Per-Run Table")
    lines.append("")
    lines.append("| run_label | mode | target_fps | frames | achieved_fps | io_mib/s | p95_ms | timestamp_monotonic |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            "| {run_label} | {read_mode} | {target_fps:.2f} | {frames} | {achieved_fps:.2f} | {io_mib_per_sec:.2f} | {p95_ms:.2f} | {timestamp_monotonic} |".format(
                **row
            )
        )

    lines.append("")
    lines.append("## Grouped Stats (mode + target_fps)")
    lines.append("")
    lines.append("| mode | target_fps | runs | mean_fps | std_fps | mean_io_mib/s | mean_p95_ms |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for key in sorted(grouped.keys(), key=lambda k: (k[0], k[2])):
        grp = grouped[key]
        mean_fps = _mean([r["achieved_fps"] for r in grp])
        std_fps = _stdev([r["achieved_fps"] for r in grp])
        mean_io = _mean([r["io_mib_per_sec"] for r in grp])
        mean_p95 = _mean([r["p95_ms"] for r in grp])
        lines.append(
            f"| {key[0]} | {key[1]} | {len(grp)} | {mean_fps:.2f} | {std_fps:.2f} | {mean_io:.2f} | {mean_p95:.2f} |"
        )

    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Replay validated scope only. No claim of live Sensor Bridge parity without dedicated provisioning.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_csv = Path(args.output_csv).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"input dir not found: {input_dir}")

    rows = load_rows(input_dir, args.glob)
    if not rows:
        raise RuntimeError("no benchmark JSON files found")

    write_csv(rows, output_csv)
    write_markdown(rows, output_md)

    print(f"wrote csv: {output_csv}")
    print(f"wrote markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
