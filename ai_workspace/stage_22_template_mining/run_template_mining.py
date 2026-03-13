# ai_workspace/stage_22_template_mining/run_template_mining.py

"""
Stage 22 - Log Template Mining
================================
Implements a lightweight Drain-style token-generalization pipeline.

Substitution pipeline (order is critical):
  1. Block IDs   : blk_-?<digits>           -> <BLK>
  2. BGL datetime: YYYY-MM-DD-HH.MM.SS.usec -> <TS>
  3. IP addresses: A.B.C.D[:port]           -> <IP>
  4. BGL date    : YYYY.MM.DD               -> <DATE>
  5. BGL node IDs: R<n>-M<n>-...           -> <NODE>
  6. File paths  : /path/to/file            -> <PATH>
  7. Hex strings : 8+ lowercase hex chars   -> <HEX>
  8. Integers    : standalone digit runs    -> <NUM>
  9. Whitespace  : collapse runs to single space

Template IDs are assigned by sorting all unique template strings
alphabetically, then numbering 1..N -- fully deterministic.

Outputs
-------
  data/intermediate/events_with_templates.csv
  data/intermediate/templates.csv
  ai_workspace/reports/stage_22_template_report.md
  ai_workspace/logs/stage_22_template_mining.log
"""

import gc
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import psutil

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE           = Path(__file__).resolve().parents[2]
INPUT_FILE     = BASE / "data/processed/events_sample_1m.csv"
OUTPUT_DIR     = BASE / "data/intermediate"
OUTPUT_FILE    = OUTPUT_DIR / "events_with_templates.csv"
TEMPLATES_FILE = OUTPUT_DIR / "templates.csv"
REPORT_FILE    = BASE / "ai_workspace/reports/stage_22_template_report.md"
LOG_FILE       = BASE / "ai_workspace/logs/stage_22_template_mining.log"

# ---------------------------------------------------------------------------
# Token substitution pipeline
# Each entry: (regex_pattern, replacement)
# Order matters -- more specific patterns precede general ones.
# ---------------------------------------------------------------------------
SUBS = [
    # 1. Block IDs (HDFS): blk_-1234567890
    (r"blk_-?\d+",                                          "<BLK>"),
    # 2. BGL datetime: 2005-12-01-06.51.06.840240
    (r"\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.\d+",       "<TS>"),
    # 3. IP address with optional port: 10.251.37.240:50010
    (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?",      "<IP>"),
    # 4. BGL date: 2005.12.01  (after IP to avoid partial conflict)
    (r"\d{4}\.\d{2}\.\d{2}",                               "<DATE>"),
    # 5. BGL node IDs: R60-M1-NC-C:J12-U01
    (r"R\d+(?:-[A-Z\d]+)+(?::[A-Z]\d+-[A-Z]\d+)?",        "<NODE>"),
    # 6. Filesystem paths: /mnt/hadoop/dfs/...
    (r"/[a-zA-Z0-9_./-]+",                                 "<PATH>"),
    # 7. Hex strings (8+ lowercase hex chars, must contain at least one letter)
    #    Catches BGL register dumps: 1eeeeeee, ffffffff, deadbeef ...
    #    Pure-digit 8+ sequences (e.g. unix timestamps) also match here
    #    so they get a consistent <HEX> token rather than <NUM>.
    (r"\b[0-9a-f]{8,}\b",                                  "<HEX>"),
    # 8. Remaining integers (any length)
    (r"\b\d+\b",                                           "<NUM>"),
    # 9. Collapse whitespace
    (r"\s+",                                               " "),
]


# ---------------------------------------------------------------------------
# Generalization (vectorized)
# ---------------------------------------------------------------------------
def generalize(series: pd.Series) -> pd.Series:
    """Apply the substitution pipeline to a string Series."""
    result = series.fillna("").astype(str)
    for pattern, replacement in SUBS:
        result = result.str.replace(pattern, replacement, regex=True)
    return result.str.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # ---- Setup ----------------------------------------------------------- #
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

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

    start_time = time.time()

    log.info("=" * 60)
    log.info("Stage 22: Log Template Mining")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Output : {OUTPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    # ---- Load ------------------------------------------------------------ #
    log.info("Loading input CSV ...")
    df = pd.read_csv(
        INPUT_FILE,
        dtype={"label": "int8"},
        low_memory=False,
    )
    n_rows = len(df)
    log.info(f"Loaded {n_rows:,} rows.  Memory: {mem_mb():.1f} MB")

    # ---- Generalize ------------------------------------------------------ #
    log.info("Applying token generalization pipeline ...")
    t0 = time.time()
    df["template_text"] = generalize(df["message"])
    gen_time = time.time() - t0
    log.info(
        f"Generalization done in {gen_time:.1f}s.  Memory: {mem_mb():.1f} MB"
    )

    # ---- Assign deterministic template IDs ------------------------------- #
    log.info("Assigning deterministic template IDs (alphabetical sort) ...")
    unique_templates = sorted(df["template_text"].unique())
    n_templates = len(unique_templates)
    template_to_id: dict[str, int] = {
        tmpl: idx + 1 for idx, tmpl in enumerate(unique_templates)
    }
    df["template_id"] = df["template_text"].map(template_to_id)
    log.info(f"Unique templates found: {n_templates:,}")

    # ---- Build template dictionary --------------------------------------- #
    log.info("Building template dictionary ...")
    tcount = (
        df.groupby("template_id")["template_text"]
        .agg(count="count", template_text="first")
        .reset_index()
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    # also add anomaly_rate per template (useful for downstream stages)
    anom = (
        df.groupby("template_id")["label"]
        .mean()
        .rename("anomaly_rate")
        .reset_index()
    )
    tcount = tcount.merge(anom, on="template_id")
    log.info(f"Template dictionary ready: {len(tcount):,} entries")

    # ---- Save outputs ---------------------------------------------------- #
    log.info(f"Saving events_with_templates.csv ({n_rows:,} rows) ...")
    col_order = [
        "timestamp", "dataset", "session_id", "message",
        "label", "template_id", "template_text",
    ]
    df[col_order].to_csv(OUTPUT_FILE, index=False)

    log.info(f"Saving templates.csv ({n_templates:,} rows) ...")
    tcount[["template_id", "template_text", "count", "anomaly_rate"]].to_csv(
        TEMPLATES_FILE, index=False
    )

    elapsed = time.time() - start_time
    log.info(f"Total elapsed: {elapsed:.1f}s")
    log.info(f"Peak memory  : {mem_mb():.1f} MB")

    # ---- Per-dataset template stats -------------------------------------- #
    per_ds = (
        df.groupby("dataset")["template_id"]
        .nunique()
        .rename("unique_templates")
        .reset_index()
    )
    log.info("Per-dataset template counts:")
    for _, row in per_ds.iterrows():
        log.info(f"  {row['dataset']}: {row['unique_templates']:,} templates")

    # ---- Top 20 templates ------------------------------------------------ #
    top20 = tcount.head(20)
    log.info("Top 20 templates by frequency:")
    for i, row in top20.iterrows():
        log.info(
            f"  {i+1:2d}. [tid={row['template_id']:4d}] "
            f"count={row['count']:,}  "
            f"anom={row['anomaly_rate']:.2%}  "
            f"'{str(row['template_text'])[:80]}'"
        )

    # ---- Frequency distribution buckets ---------------------------------- #
    freq_bins = [1, 2, 5, 10, 50, 100, 500, 1000, 5000, 10000, float("inf")]
    freq_labels = ["1", "2-4", "5-9", "10-49", "50-99",
                   "100-499", "500-999", "1k-4k", "5k-9k", "10k+"]
    tcount["freq_bin"] = pd.cut(
        tcount["count"],
        bins=[0] + freq_bins,
        labels=["0"] + freq_labels,
        right=True,
    )
    freq_dist = tcount["freq_bin"].value_counts().sort_index()

    # ---- Generate report ------------------------------------------------- #
    log.info(f"Writing report to {REPORT_FILE} ...")

    input_mb  = INPUT_FILE.stat().st_size  / 1024 ** 2
    output_mb = OUTPUT_FILE.stat().st_size / 1024 ** 2
    tmpl_mb   = TEMPLATES_FILE.stat().st_size / 1024 ** 2

    lines = [
        "# Stage 22 Template Mining Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        f"**Input:** `{INPUT_FILE.name}`  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Input rows | {n_rows:,} |",
        f"| Unique templates | {n_templates:,} |",
        f"| Avg rows / template | {n_rows / n_templates:,.1f} |",
        f"| Generalization time | {gen_time:.1f}s |",
        f"| Total elapsed | {elapsed:.1f}s |",
        f"| Peak memory | {mem_mb():.1f} MB |",
        f"| Input file size | {input_mb:.1f} MB |",
        f"| Output CSV size | {output_mb:.1f} MB |",
        f"| Templates CSV size | {tmpl_mb:.2f} MB |",
        "",
        "---",
        "",
        "## Token Substitution Pipeline",
        "",
        "| Step | Pattern | Token |",
        "|-----:|---------|-------|",
    ]
    step_descs = [
        ("Block IDs",       r"blk_-?\\d+",                            "<BLK>"),
        ("BGL datetime",    r"\\d{4}-\\d{2}-\\d{2}-\\d{2}\\.\\d{2}\\.\\d{2}\\.\\d+", "<TS>"),
        ("IP address",      r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}(?::\\d+)?",  "<IP>"),
        ("BGL date",        r"\\d{4}\\.\\d{2}\\.\\d{2}",             "<DATE>"),
        ("BGL node ID",     r"R\\d+(?:-[A-Z\\d]+)+(?::[A-Z]\\d+-[A-Z]\\d+)?", "<NODE>"),
        ("File path",       r"/[a-zA-Z0-9_./\\-]+",                  "<PATH>"),
        ("Hex string",      r"\\b[0-9a-f]{8,}\\b",                   "<HEX>"),
        ("Integer",         r"\\b\\d+\\b",                            "<NUM>"),
        ("Whitespace",      r"\\s+",                                  "` `"),
    ]
    for i, (desc, pat, tok) in enumerate(step_descs, 1):
        lines.append(f"| {i} | {desc}: `{pat}` | `{tok}` |")

    lines += [
        "",
        "---",
        "",
        "## Per-Dataset Template Counts",
        "",
        "| Dataset | Unique Templates |",
        "|---------|----------------:|",
    ]
    for _, row in per_ds.iterrows():
        lines.append(f"| {row['dataset']} | {row['unique_templates']:,} |")

    lines += [
        "",
        "---",
        "",
        "## Template Frequency Distribution",
        "",
        "| Frequency bucket | # Templates |",
        "|------------------|------------:|",
    ]
    for bucket, cnt in freq_dist.items():
        if cnt > 0:
            lines.append(f"| {bucket} | {cnt:,} |")

    lines += [
        "",
        "---",
        "",
        "## Top 20 Templates by Frequency",
        "",
        "| Rank | TID | Count | Anomaly Rate | Template (first 120 chars) |",
        "|-----:|----:|------:|-------------:|---------------------------|",
    ]
    for i, row in top20.iterrows():
        tmpl_short = str(row["template_text"])[:120].replace("|", "\\|")
        lines.append(
            f"| {i+1} | {row['template_id']} | {row['count']:,} "
            f"| {row['anomaly_rate']:.2%} | `{tmpl_short}` |"
        )

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Rows | Size |",
        "|------|-----:|-----:|",
        f"| `events_with_templates.csv` | {n_rows:,} | {output_mb:.1f} MB |",
        f"| `templates.csv` | {n_templates:,} | {tmpl_mb:.2f} MB |",
        "",
        "---",
        "",
        "*Stage 22 completed successfully.*",
    ]

    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Report saved.")

    # ---- Console summary ------------------------------------------------- #
    print()
    print("=" * 60)
    print(f"  Input rows        : {n_rows:,}")
    print(f"  Unique templates  : {n_templates:,}")
    print(f"  Avg rows/template : {n_rows / n_templates:,.1f}")
    print()
    print("  Per-dataset templates:")
    for _, row in per_ds.iterrows():
        print(f"    {row['dataset']}: {row['unique_templates']:,}")
    print()
    print("  Top 10 templates by frequency:")
    for i, row in tcount.head(10).iterrows():
        print(
            f"    {i+1:2d}. [tid={row['template_id']:4d}] "
            f"n={row['count']:6,}  anom={row['anomaly_rate']:.1%}  "
            f"'{str(row['template_text'])[:70]}'"
        )
    print()
    print("  Generated files:")
    print(f"    {OUTPUT_FILE}")
    print(f"    {TEMPLATES_FILE}")
    print(f"    {REPORT_FILE}")
    print(f"    {LOG_FILE}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s   |   Peak mem: {mem_mb():.1f} MB")
    print("=" * 60)
    print()
    print("Stage 22 completed successfully.")


if __name__ == "__main__":
    main()
