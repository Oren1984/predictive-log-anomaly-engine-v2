# ai_workspace/stage_21_sampling/run_sampling.py

"""
Stage 21 – Stratified Sampling
================================
Generates a stratified 1,000,000-row sample from events_unified.csv,
stratified by (label, dataset).  Two-pass, chunked approach to keep
peak memory low.

Output
------
data/processed/events_sample_1m.csv
ai_workspace/reports/stage_21_sampling_report.md
ai_workspace/logs/stage_21_sampling.log
"""

import gc
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42
TARGET_ROWS = 1_000_000
CHUNK_SIZE = 500_000

BASE = Path(__file__).resolve().parents[2]          # repo root
INPUT_FILE  = BASE / "data/processed/events_unified.csv"
OUTPUT_FILE = BASE / "data/processed/events_sample_1m.csv"
REPORT_FILE = BASE / "ai_workspace/reports/stage_21_sampling_report.md"
LOG_FILE    = BASE / "ai_workspace/logs/stage_21_sampling.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

process = psutil.Process(os.getpid())


def mem_mb() -> float:
    return process.memory_info().rss / 1024 / 1024


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    start_time = time.time()
    log.info("=" * 60)
    log.info("Stage 21: Stratified Sampling")
    log.info(f"Target rows : {TARGET_ROWS:,}")
    log.info(f"Seed        : {SEED}")
    log.info(f"Chunk size  : {CHUNK_SIZE:,}")
    log.info(f"Input file  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    # -----------------------------------------------------------------------
    # Pass 1 – count rows per (label, dataset) group (only 2 columns read)
    # -----------------------------------------------------------------------
    log.info("Pass 1: counting group sizes ...")
    group_counts: dict[tuple, int] = defaultdict(int)
    total_rows = 0

    for chunk in pd.read_csv(INPUT_FILE, usecols=["label", "dataset"],
                              chunksize=CHUNK_SIZE, dtype={"label": "int8"}):
        for (label, dataset), cnt in chunk.groupby(
            ["label", "dataset"], observed=True
        ).size().items():
            group_counts[(int(label), str(dataset))] += int(cnt)
        total_rows += len(chunk)
        del chunk
        gc.collect()

    log.info(f"Total rows    : {total_rows:,}")
    log.info(f"Groups found  : {len(group_counts)}")
    for g, cnt in sorted(group_counts.items()):
        log.info(f"  {g} → {cnt:,} rows  ({cnt/total_rows:.4%})")
    log.info(f"Memory after pass 1: {mem_mb():.1f} MB")

    if total_rows < TARGET_ROWS:
        log.error(
            f"Dataset has only {total_rows:,} rows, which is less than "
            f"the target {TARGET_ROWS:,}.  Aborting."
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Compute per-group sample sizes (proportional, integer, sum = TARGET_ROWS)
    # -----------------------------------------------------------------------
    groups = sorted(group_counts.keys())
    target_per_group: dict[tuple, int] = {}
    allocated = 0

    for i, g in enumerate(groups):
        if i == len(groups) - 1:
            # Give the remainder to the last group so the total is exact
            target_per_group[g] = TARGET_ROWS - allocated
        else:
            t = round(group_counts[g] / total_rows * TARGET_ROWS)
            target_per_group[g] = t
            allocated += t

    log.info("Per-group sample targets:")
    for g in groups:
        t = target_per_group[g]
        c = group_counts[g]
        log.info(f"  {g}: sample {t:,} / {c:,}  (frac={t/c:.6f})")
    log.info(f"Total allocated: {sum(target_per_group.values()):,}")

    # Running counters for deterministic proportional sampling across chunks
    remaining_target: dict[tuple, int] = dict(target_per_group)
    remaining_total:  dict[tuple, int] = dict(group_counts)

    # -----------------------------------------------------------------------
    # Pass 2 – read full CSV in chunks, sample proportionally per group
    # -----------------------------------------------------------------------
    log.info("Pass 2: sampling rows ...")
    rng = np.random.default_rng(SEED)
    sampled_parts: list[pd.DataFrame] = []
    rows_collected = 0

    for chunk_idx, chunk in enumerate(
        pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE,
                    dtype={"label": "int8"},
                    low_memory=False)
    ):
        chunk["label"] = chunk["label"].astype(int)

        chunk_sampled: list[pd.DataFrame] = []
        for (label, dataset), grp in chunk.groupby(
            ["label", "dataset"], observed=True
        ):
            g = (int(label), str(dataset))
            if g not in remaining_target:
                continue
            rt = remaining_target[g]
            rc = remaining_total[g]
            if rt <= 0 or rc <= 0:
                remaining_total[g] -= len(grp)
                continue

            # How many rows to draw from this group's chunk slice
            n_take = round(rt / rc * len(grp))
            n_take = min(n_take, len(grp), rt)
            n_take = max(n_take, 0)

            if n_take > 0:
                seed_i = int(rng.integers(0, 2**31))
                chunk_sampled.append(grp.sample(n=n_take, random_state=seed_i))
                remaining_target[g] -= n_take

            remaining_total[g] -= len(grp)

        if chunk_sampled:
            part = pd.concat(chunk_sampled, ignore_index=True)
            sampled_parts.append(part)
            rows_collected += len(part)

        del chunk
        gc.collect()

        if chunk_idx % 5 == 0 or chunk_idx == 0:
            log.info(
                f"  chunk {chunk_idx:3d} processed | "
                f"collected {rows_collected:,} rows | "
                f"mem {mem_mb():.1f} MB"
            )

    log.info(f"Sampling complete. Rows collected: {rows_collected:,}")

    # -----------------------------------------------------------------------
    # Combine, shuffle, save
    # -----------------------------------------------------------------------
    log.info("Combining sampled chunks ...")
    result = pd.concat(sampled_parts, ignore_index=True)
    del sampled_parts
    gc.collect()

    log.info(f"Total sampled rows before shuffle: {len(result):,}")
    log.info(f"Memory before shuffle: {mem_mb():.1f} MB")

    result = result.sample(frac=1, random_state=SEED).reset_index(drop=True)

    log.info(f"Saving to {OUTPUT_FILE} ...")
    result.to_csv(OUTPUT_FILE, index=False)
    log.info("Output saved.")

    elapsed = time.time() - start_time
    log.info(f"Elapsed time: {elapsed:.1f}s")
    log.info(f"Memory after save: {mem_mb():.1f} MB")

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------
    label_dist   = result["label"].value_counts().sort_index()
    dataset_dist = result["dataset"].value_counts().sort_index()
    top20_msgs   = result["message"].value_counts().head(20)

    input_size_mb  = INPUT_FILE.stat().st_size  / 1024 ** 2
    output_size_mb = OUTPUT_FILE.stat().st_size / 1024 ** 2
    peak_mem_mb    = mem_mb()

    log.info("--- Label distribution ---")
    for lbl, cnt in label_dist.items():
        log.info(f"  label={lbl}: {cnt:,}  ({cnt/len(result):.4%})")
    log.info("--- Dataset distribution ---")
    for ds, cnt in dataset_dist.items():
        log.info(f"  dataset={ds}: {cnt:,}  ({cnt/len(result):.4%})")
    log.info("--- Top 20 messages ---")
    for i, (msg, cnt) in enumerate(top20_msgs.items(), 1):
        log.info(f"  {i:2d}. [{cnt:,}] {str(msg)[:100]}")

    # -----------------------------------------------------------------------
    # Generate report
    # -----------------------------------------------------------------------
    log.info(f"Writing report to {REPORT_FILE} ...")

    lines = [
        "# Stage 21 Sampling Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        f"**Random seed:** {SEED}  ",
        f"**Stratified by:** `label`, `dataset`  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Input file | `{INPUT_FILE.name}` |",
        f"| Total input rows | {total_rows:,} |",
        f"| Sampled rows | {len(result):,} |",
        f"| Sampling fraction | {len(result)/total_rows:.4%} |",
        f"| Input file size | {input_size_mb:.1f} MB |",
        f"| Output file size | {output_size_mb:.1f} MB |",
        f"| Peak process memory | {peak_mem_mb:.1f} MB |",
        f"| Execution time | {elapsed:.1f}s |",
        "",
        "---",
        "",
        "## Label Distribution",
        "",
        "| Label | Count | Fraction |",
        "|-------|------:|----------:|",
    ]
    for lbl, cnt in label_dist.items():
        lines.append(f"| {lbl} | {cnt:,} | {cnt/len(result):.4%} |")

    lines += [
        "",
        "---",
        "",
        "## Dataset Distribution",
        "",
        "| Dataset | Count | Fraction |",
        "|---------|------:|----------:|",
    ]
    for ds, cnt in dataset_dist.items():
        lines.append(f"| {ds} | {cnt:,} | {cnt/len(result):.4%} |")

    lines += [
        "",
        "---",
        "",
        "## Per-Group Sample Details",
        "",
        "| Label | Dataset | Input Rows | Sampled Rows | Fraction |",
        "|------:|---------|----------:|-------------:|----------:|",
    ]
    actual_group_counts = result.groupby(["label", "dataset"]).size().to_dict()
    for g in sorted(group_counts.keys()):
        label, dataset = g
        total_g   = group_counts[g]
        sampled_g = actual_group_counts.get(g, 0)
        frac      = sampled_g / total_g if total_g > 0 else 0.0
        lines.append(
            f"| {label} | {dataset} | {total_g:,} | {sampled_g:,} | {frac:.4%} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Top 20 Frequent Messages",
        "",
        "| Rank | Count | Message (first 120 chars) |",
        "|-----:|------:|--------------------------|",
    ]
    for i, (msg, cnt) in enumerate(top20_msgs.items(), 1):
        msg_short = str(msg)[:120].replace("|", "\\|")
        lines.append(f"| {i} | {cnt:,} | `{msg_short}` |")

    lines += [
        "",
        "---",
        "",
        "## Memory Estimation",
        "",
        "Peak memory was measured using `psutil` on the live process.",
        "",
        f"- **Input file:** {input_size_mb:.1f} MB on disk",
        f"- **Output file:** {output_size_mb:.1f} MB on disk",
        f"- **Peak RSS:** {peak_mem_mb:.1f} MB",
        f"- **Chunk size:** {CHUNK_SIZE:,} rows per chunk",
        "",
        "> Two-pass chunked reading ensures the full input is never held",
        "> in memory at once; only ~1M sampled rows accumulate between passes.",
        "",
        "---",
        "",
        "*Stage 21 completed successfully.*",
    ]

    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Report saved.")

    # -----------------------------------------------------------------------
    # Final console summary
    # -----------------------------------------------------------------------
    print()
    print("=" * 60)
    print(f"  Total input rows   : {total_rows:,}")
    print(f"  Sampled rows       : {len(result):,}")
    print(f"  Sampling fraction  : {len(result)/total_rows:.4%}")
    print()
    print("  Label distribution:")
    for lbl, cnt in label_dist.items():
        print(f"    label={lbl}: {cnt:,}  ({cnt/len(result):.4%})")
    print()
    print("  Dataset distribution:")
    for ds, cnt in dataset_dist.items():
        print(f"    dataset={ds}: {cnt:,}  ({cnt/len(result):.4%})")
    print()
    print("  Generated files:")
    print(f"    {OUTPUT_FILE}")
    print(f"    {REPORT_FILE}")
    print(f"    {LOG_FILE}")
    print(f"    {Path(__file__)}")
    print()
    print(f"  Execution time : {elapsed:.1f}s")
    print(f"  Peak memory    : {peak_mem_mb:.1f} MB")
    print("=" * 60)
    print()
    print("Stage 21 completed successfully.")


if __name__ == "__main__":
    main()
