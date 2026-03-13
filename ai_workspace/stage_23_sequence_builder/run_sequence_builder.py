# ai_workspace/stage_23_sequence_builder/run_sequence_builder.py

"""
Stage 23 - Session Sequence Builder
=====================================
Groups log events by session_id to produce:

  A) session_sequences.csv
       session_id, dataset, label, sequence_length,
       ordered_template_sequence, unique_template_count

  B) session_features.csv
       session_id, dataset, label, sequence_length,
       tid_<N> columns (top-100 template counts, raw + normalised)

Event order within each session is the original row order from the input
(events_with_templates.csv is already in chronological order per session).

Outputs
-------
  data/intermediate/session_sequences.csv
  data/intermediate/session_features.csv
  ai_workspace/reports/stage_23_sequence_report.md
  ai_workspace/logs/stage_23_sequence.log
"""

import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE              = Path(__file__).resolve().parents[2]
INPUT_FILE        = BASE / "data/intermediate/events_with_templates.csv"
SEQ_OUTPUT        = BASE / "data/intermediate/session_sequences.csv"
FEAT_OUTPUT       = BASE / "data/intermediate/session_features.csv"
REPORT_FILE       = BASE / "ai_workspace/reports/stage_23_sequence_report.md"
LOG_FILE          = BASE / "ai_workspace/logs/stage_23_sequence.log"

TOP_N_TEMPLATES   = 100   # how many template columns to include in features

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
def setup_logging() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def mem_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def build_sequences(df: pd.DataFrame, log: logging.Logger) -> pd.DataFrame:
    """
    Group by session_id, preserve row order, return session_sequences DataFrame.
    """
    log.info("Building session sequences ...")

    # template_id as int is already set; coerce to int32 to save memory
    df["template_id"] = df["template_id"].astype("int32")

    # Aggregate per session (row order in df == original event order)
    grp = df.groupby("session_id", sort=False)

    seq_df = grp["template_id"].agg(
        ordered_template_sequence=lambda ids: ",".join(ids.astype(str)),
        sequence_length="count",
        unique_template_count="nunique",
    ).reset_index()

    # dataset: take first (all events in a session share the same dataset)
    meta = grp.agg(
        dataset=("dataset", "first"),
        label=("label", "max"),       # anomalous if any event is anomalous
    ).reset_index()

    sessions = meta.merge(seq_df, on="session_id")
    sessions = sessions[[
        "session_id", "dataset", "label",
        "sequence_length", "ordered_template_sequence", "unique_template_count",
    ]]

    log.info(f"Sessions built: {len(sessions):,}")
    return sessions


def build_features(df: pd.DataFrame, sessions: pd.DataFrame,
                   log: logging.Logger) -> pd.DataFrame:
    """
    Build numeric feature matrix:
      - raw counts for top-N templates
      - normalised counts (divided by sequence_length)
    Uses a pivot approach that avoids a Python-level loop over sessions.
    """
    log.info(f"Selecting top {TOP_N_TEMPLATES} templates by overall frequency ...")
    top_tids = (
        df["template_id"]
        .value_counts()
        .head(TOP_N_TEMPLATES)
        .index
        .tolist()
    )
    log.info(f"Top-{TOP_N_TEMPLATES} template IDs selected.")

    # Filter to top-N template events only
    log.info("Filtering events to top-N templates ...")
    df_top = df[df["template_id"].isin(top_tids)][["session_id", "template_id"]].copy()

    log.info("Counting template occurrences per session (pivot) ...")
    # Count occurrences: (session_id, template_id) -> count
    counts = (
        df_top.groupby(["session_id", "template_id"], sort=False)
        .size()
        .reset_index(name="cnt")
    )

    # Pivot to wide format
    feat_wide = counts.pivot(
        index="session_id", columns="template_id", values="cnt"
    ).fillna(0).astype("int32")

    # Rename columns: tid_<N>
    feat_wide.columns = [f"tid_{c}" for c in feat_wide.columns]
    feat_wide = feat_wide.reset_index()

    # Merge with session metadata
    meta_cols = sessions[["session_id", "dataset", "label", "sequence_length"]]
    feat_df = meta_cols.merge(feat_wide, on="session_id", how="left")

    # Fill sessions that had zero top-N events with 0
    tid_cols = [c for c in feat_df.columns if c.startswith("tid_")]
    feat_df[tid_cols] = feat_df[tid_cols].fillna(0).astype("int32")

    # Normalised columns (freq / sequence_length)
    log.info("Computing normalised template frequencies ...")
    seq_len = feat_df["sequence_length"].values.reshape(-1, 1)
    raw_vals = feat_df[tid_cols].values.astype("float32")
    norm_vals = np.divide(raw_vals, seq_len, where=seq_len > 0,
                          out=np.zeros_like(raw_vals))
    norm_cols = [c + "_norm" for c in tid_cols]
    norm_df = pd.DataFrame(norm_vals, columns=norm_cols, index=feat_df.index)
    feat_df = pd.concat([feat_df, norm_df], axis=1)

    log.info(f"Feature matrix shape: {feat_df.shape}")
    return feat_df


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(sessions: pd.DataFrame, feat_df: pd.DataFrame,
                 elapsed: float, peak_mem: float, log: logging.Logger) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    n_sessions        = len(sessions)
    avg_len           = sessions["sequence_length"].mean()
    med_len           = sessions["sequence_length"].median()
    max_len           = sessions["sequence_length"].max()
    vocab_size        = sessions["ordered_template_sequence"].str.split(",").explode().nunique()

    label_dist        = sessions["label"].value_counts().sort_index()
    dataset_dist      = sessions["dataset"].value_counts()
    top10             = sessions.nlargest(10, "sequence_length")[
        ["session_id", "dataset", "label", "sequence_length"]
    ]

    tid_cols = [c for c in feat_df.columns if c.startswith("tid_") and not c.endswith("_norm")]
    top_tid  = feat_df[tid_cols].sum().idxmax() if tid_cols else "N/A"

    lines = [
        "# Stage 23 Sequence Builder Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        f"**Peak memory:** {peak_mem:.1f} MB  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total sessions | {n_sessions:,} |",
        f"| Avg sequence length | {avg_len:.2f} |",
        f"| Median sequence length | {med_len:.1f} |",
        f"| Max sequence length | {max_len:,} |",
        f"| Template vocabulary size | {vocab_size:,} |",
        f"| Feature columns (top-N raw+norm) | {len(tid_cols)*2} |",
        f"| Total elapsed | {elapsed:.1f}s |",
        f"| Peak memory | {peak_mem:.1f} MB |",
        "",
        "---",
        "",
        "## Label Distribution (session level)",
        "",
        "| Label | Sessions | Pct |",
        "|------:|---------:|----:|",
    ]
    for lbl, cnt in label_dist.items():
        lines.append(f"| {lbl} | {cnt:,} | {cnt/n_sessions:.2%} |")

    lines += [
        "",
        "---",
        "",
        "## Dataset Distribution",
        "",
        "| Dataset | Sessions | Pct |",
        "|---------|--------:|----:|",
    ]
    for ds, cnt in dataset_dist.items():
        lines.append(f"| {ds} | {cnt:,} | {cnt/n_sessions:.2%} |")

    lines += [
        "",
        "---",
        "",
        "## Top 10 Longest Sessions",
        "",
        "| session_id | dataset | label | sequence_length |",
        "|------------|---------|------:|----------------:|",
    ]
    for _, row in top10.iterrows():
        lines.append(
            f"| {row['session_id']} | {row['dataset']} | {row['label']} | {row['sequence_length']:,} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Shape |",
        "|------|-------|",
        f"| `session_sequences.csv` | {n_sessions:,} rows x {6} cols |",
        f"| `session_features.csv`  | {feat_df.shape[0]:,} rows x {feat_df.shape[1]} cols |",
        "",
        "---",
        "",
        "*Stage 23 completed successfully.*",
    ]

    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"Report saved: {REPORT_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log = setup_logging()
    start_time = time.time()

    log.info("=" * 60)
    log.info("Stage 23: Session Sequence Builder")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    # ---- Load ------------------------------------------------------------ #
    try:
        log.info("Loading events_with_templates.csv ...")
        df = pd.read_csv(
            INPUT_FILE,
            usecols=["session_id", "dataset", "label", "template_id"],
            dtype={"label": "int8", "template_id": "int32"},
        )
        n_rows = len(df)
        log.info(f"Loaded {n_rows:,} rows.  Memory: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to load input: {exc}")
        raise

    # ---- Build sequences ------------------------------------------------- #
    try:
        sessions = build_sequences(df, log)
        log.info(f"Memory after sequences: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to build sequences: {exc}")
        raise

    # ---- Build features -------------------------------------------------- #
    try:
        feat_df = build_features(df, sessions, log)
        log.info(f"Memory after features: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to build features: {exc}")
        raise

    # ---- Save outputs ---------------------------------------------------- #
    try:
        SEQ_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Saving session_sequences.csv ({len(sessions):,} rows) ...")
        sessions.to_csv(SEQ_OUTPUT, index=False)

        log.info(f"Saving session_features.csv ({feat_df.shape[0]:,} rows, {feat_df.shape[1]} cols) ...")
        feat_df.to_csv(FEAT_OUTPUT, index=False)
    except Exception as exc:
        log.error(f"Failed to save outputs: {exc}")
        raise

    elapsed  = time.time() - start_time
    peak_mem = mem_mb()
    log.info(f"Total elapsed: {elapsed:.1f}s")
    log.info(f"Peak memory  : {peak_mem:.1f} MB")

    # ---- Report ---------------------------------------------------------- #
    try:
        write_report(sessions, feat_df, elapsed, peak_mem, log)
    except Exception as exc:
        log.error(f"Failed to write report: {exc}")
        raise

    # ---- Determine top template by frequency ----------------------------- #
    tid_cols = [c for c in feat_df.columns if c.startswith("tid_") and not c.endswith("_norm")]
    top_tid  = feat_df[tid_cols].sum().idxmax() if tid_cols else "N/A"
    avg_len  = sessions["sequence_length"].mean()

    # ---- Console summary ------------------------------------------------- #
    print()
    print("=" * 60)
    print(f"  Total sessions    : {len(sessions):,}")
    print(f"  Avg seq length    : {avg_len:.2f}")
    print(f"  Top template (col): {top_tid}")
    print()
    print("  Generated files:")
    print(f"    {SEQ_OUTPUT}")
    print(f"    {FEAT_OUTPUT}")
    print(f"    {REPORT_FILE}")
    print(f"    {LOG_FILE}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s   |   Peak mem: {peak_mem:.1f} MB")
    print("=" * 60)
    print()
    print("Stage 23 completed successfully.")


if __name__ == "__main__":
    main()
