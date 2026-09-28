#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from collections import Counter, defaultdict
from typing import Dict, Iterable, List

import yaml

REQUIRED_COLUMNS = {
    "run_id",
    "step_id",
    "started",
    "stopped",
    "wall_min",
    "hands_min",
    "brain_0_5",
    "type_I_M_A_W",
    "blocker",
    "what_would_have_deleted_this_step",
}


def load_config(path: pathlib.Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def parse_float(raw: str, field: str, row_num: int, file_path: pathlib.Path) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{file_path}:{row_num} invalid {field}: {raw!r}") from exc


def iter_rows(log_paths: Iterable[pathlib.Path]) -> List[dict]:
    rows: List[dict] = []
    for log_path in log_paths:
        with log_path.open(newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError(f"{log_path}: missing CSV header")
            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise ValueError(f"{log_path}: missing columns: {sorted(missing)}")

            for i, row in enumerate(reader, start=2):
                if not row["what_would_have_deleted_this_step"].strip():
                    raise ValueError(
                        f"{log_path}:{i} missing what_would_have_deleted_this_step (use 'nothing' if none)"
                    )

                hands = parse_float(row["hands_min"], "hands_min", i, log_path)
                wall = parse_float(row["wall_min"], "wall_min", i, log_path)
                brain = parse_float(row["brain_0_5"], "brain_0_5", i, log_path)
                if not (0 <= brain <= 5):
                    raise ValueError(f"{log_path}:{i} brain_0_5 out of range: {brain}")

                row_type = row["type_I_M_A_W"].strip()
                if row_type not in {"I", "M", "A", "W"}:
                    raise ValueError(f"{log_path}:{i} invalid type_I_M_A_W: {row_type!r}")

                rows.append(
                    {
                        **row,
                        "wall_min": wall,
                        "hands_min": hands,
                        "brain_0_5": brain,
                        "type_I_M_A_W": row_type,
                        "bm": hands * brain,
                    }
                )
    return rows


def summarize(rows: List[dict], targets: dict) -> str:
    by_run: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        by_run[row["run_id"]].append(row)

    out: List[str] = []
    out.append("Northbound Ops Ledger Summary")
    out.append("=")

    all_wall = sum(r["wall_min"] for r in rows)
    all_hands = sum(r["hands_min"] for r in rows)
    all_bm = sum(r["bm"] for r in rows)

    type_bm = Counter()
    for r in rows:
        type_bm[r["type_I_M_A_W"]] += r["bm"]

    for run_id in sorted(by_run):
        run_rows = by_run[run_id]
        wall = sum(r["wall_min"] for r in run_rows)
        hands = sum(r["hands_min"] for r in run_rows)
        bm = sum(r["bm"] for r in run_rows)
        ratio = (hands / wall) if wall else 0.0
        ingenuity_share = (sum(r["bm"] for r in run_rows if r["type_I_M_A_W"] == "I") / bm) if bm else 0.0

        out.append(f"\nRun {run_id}")
        out.append(f"- WALL: {wall:.1f} min")
        out.append(f"- HANDS: {hands:.1f} min")
        out.append(f"- BM: {bm:.1f}")
        out.append(f"- HANDS/WALL: {ratio:.3f} (target <= {targets['hands_to_wall_max_ratio']:.3f})")
        out.append(f"- Ingenuity BM share: {ingenuity_share:.3f} (target >= {targets['ingenuity_bm_share_min']:.3f})")

    all_ratio = (all_hands / all_wall) if all_wall else 0.0
    all_ingenuity_share = (type_bm["I"] / all_bm) if all_bm else 0.0

    out.append("\nCombined")
    out.append(f"- WALL: {all_wall:.1f} min")
    out.append(f"- HANDS: {all_hands:.1f} min")
    out.append(f"- BM: {all_bm:.1f} (target <= {targets['bm_total_per_beacon_max']})")
    out.append(f"- Type BM shares: I={type_bm['I']/all_bm:.3f} M={type_bm['M']/all_bm:.3f} A={type_bm['A']/all_bm:.3f} W={type_bm['W']/all_bm:.3f}" if all_bm else "- Type BM shares: n/a")

    pass_hands_ratio = all_ratio <= targets["hands_to_wall_max_ratio"]
    pass_bm_total = all_bm <= targets["bm_total_per_beacon_max"]
    pass_ingenuity = all_ingenuity_share >= targets["ingenuity_bm_share_min"]
    out.append("\nPass/Fail")
    out.append(f"- HANDS/WALL <= target: {'PASS' if pass_hands_ratio else 'FAIL'}")
    out.append(f"- BM total <= target: {'PASS' if pass_bm_total else 'FAIL'}")
    out.append(f"- Ingenuity BM share >= target: {'PASS' if pass_ingenuity else 'FAIL'}")

    by_step_bm = Counter()
    by_step_freq = Counter()
    for r in rows:
        by_step_bm[r["step_id"]] += r["bm"]
        by_step_freq[r["step_id"]] += 1

    ranking = sorted(
        ((step, by_step_bm[step] * by_step_freq[step], by_step_bm[step], by_step_freq[step]) for step in by_step_bm),
        key=lambda x: x[1],
        reverse=True,
    )

    out.append("\nKill order (BM × frequency)")
    for step, score, bm, freq in ranking[:10]:
        out.append(f"- {step}: {score:.1f} (bm={bm:.1f}, freq={freq})")

    blockers = Counter(r["blocker"].strip() for r in rows if r["blocker"].strip())
    if blockers:
        out.append("\nTop blockers")
        for blocker, count in blockers.most_common(10):
            out.append(f"- {blocker}: {count}")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Stage 4/5/6 practice-run logs")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("ops-ledger.stages-4-5-6.yaml"),
        help="Path to ops ledger config",
    )
    parser.add_argument(
        "--logs",
        type=pathlib.Path,
        nargs="*",
        help="CSV log files. Defaults to ops/logs/run-*.csv and *.baseline.csv",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    targets = cfg["targets"]

    if args.logs:
        logs = args.logs
    else:
        logs_dir = pathlib.Path("ops/logs")
        logs = sorted(set(logs_dir.glob("run-*.csv")))

    if not logs:
        raise ValueError("No log files found. Add run logs under ops/logs/.")

    rows = iter_rows(logs)
    print(summarize(rows, targets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
