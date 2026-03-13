# ai_workspace/stage_23_sequence_builder/run_sequence_builder_v2.py

"""
Stage 23 V2 - Session Sequence Builder (Enhanced)
===================================================
Extends V1 with:
  - unique_ratio  (unique_template_count / sequence_length)
  - template_entropy (Shannon entropy of template distribution per session)
  - Top-100 bigram/transition frequency features (raw + normalised)
    Bigram = "tidA>tidB" for consecutive events within a session

Outputs
-------
  data/intermediate/session_sequences_v2.csv
  data/intermediate/session_features_v2.csv
  ai_workspace/reports/stage_23_sequence_report_v2.md
  ai_workspace/logs/stage_23_sequence_v2.log
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
BASE         = Path(__file__).resolve().parents[2]
INPUT_FILE   = BASE / "data/intermediate/events_with_templates.csv"
SEQ_OUTPUT   = BASE / "data/intermediate/session_sequences_v2.csv"
FEAT_OUTPUT  = BASE / "data/intermediate/session_features_v2.csv"
REPORT_FILE  = BASE / "ai_workspace/reports/stage_23_sequence_report_v2.md"
LOG_FILE     = BASE / "ai_workspace/logs/stage_23_sequence_v2.log"

TOP_N_TEMPLATES = 100
TOP_M_BIGRAMS   = 100

# ---------------------------------------------------------------------------
# Logging / memory
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
# Step 1: session sequences
# ---------------------------------------------------------------------------
def build_sequences(df: pd.DataFrame, log: logging.Logger) -> pd.DataFrame:
    """Group by session_id (preserving row order) -> session_sequences_v2."""
    log.info("Building session sequences ...")

    grp = df.groupby("session_id", sort=False)

    seq_df = grp["template_id"].agg(
        ordered_template_sequence=lambda ids: ",".join(ids.astype(str)),
        sequence_length="count",
        unique_template_count="nunique",
    ).reset_index()

    meta = grp.agg(
        dataset=("dataset", "first"),
        label=("label", "max"),
    ).reset_index()

    sessions = meta.merge(seq_df, on="session_id")
    sessions = sessions[[
        "session_id", "dataset", "label",
        "sequence_length", "ordered_template_sequence", "unique_template_count",
    ]]
    log.info(f"Sessions built: {len(sessions):,}")
    return sessions


# ---------------------------------------------------------------------------
# Step 2: template entropy
# ---------------------------------------------------------------------------
def compute_entropy(df: pd.DataFrame, sessions: pd.DataFrame,
                    log: logging.Logger) -> pd.Series:
    """
    Shannon entropy of template_id distribution within each session.
    H = -sum(p * log2(p))  where p = count(tid) / sequence_length
    Returns a Series indexed by session_id.
    """
    log.info("Computing per-session template entropy ...")

    # (session_id, template_id) -> count
    tid_counts = (
        df.groupby(["session_id", "template_id"], sort=False)
        .size()
        .reset_index(name="cnt")
    )
    tid_counts = tid_counts.merge(
        sessions[["session_id", "sequence_length"]], on="session_id"
    )
    tid_counts["p"] = tid_counts["cnt"] / tid_counts["sequence_length"]
    # clip to avoid log2(0)
    tid_counts["h"] = -tid_counts["p"] * np.log2(tid_counts["p"].clip(lower=1e-12))
    entropy_s = (
        tid_counts.groupby("session_id")["h"]
        .sum()
        .rename("template_entropy")
    )
    log.info("Template entropy computed.")
    return entropy_s


# ---------------------------------------------------------------------------
# Step 3: bigrams
# ---------------------------------------------------------------------------
def build_bigram_features(df: pd.DataFrame, sessions: pd.DataFrame,
                           log: logging.Logger) -> tuple[pd.DataFrame, list, list]:
    """
    Build bigram features for each session.

    Returns:
        feat_wide  : DataFrame (session_id, bgram_<X> columns)
        top_bigrams: list of top-M bigram strings (global frequency)
        all_bigrams_ranked: list of all bigrams sorted by freq (for report)
    """
    log.info("Building bigrams (consecutive template pairs per session) ...")

    # Shift template_id within session to get 'next' event
    # sort=False preserves original row order
    df = df.copy()
    df["next_tid"] = df.groupby("session_id", sort=False)["template_id"].shift(-1)
    # Drop last event of each session (no successor)
    bigram_df = df.dropna(subset=["next_tid"]).copy()
    bigram_df["next_tid"] = bigram_df["next_tid"].astype("int32")
    bigram_df["bigram"] = (
        bigram_df["template_id"].astype(str)
        + ">"
        + bigram_df["next_tid"].astype(str)
    )
    n_total_bigrams = bigram_df["bigram"].nunique()
    log.info(f"Total unique bigrams (global): {n_total_bigrams:,}")

    # Global bigram frequency
    global_freq = bigram_df["bigram"].value_counts()
    top_bigrams = global_freq.head(TOP_M_BIGRAMS).index.tolist()
    log.info(f"Top-{TOP_M_BIGRAMS} bigrams selected.")

    # Filter to top-M bigrams only
    bigram_top = bigram_df[bigram_df["bigram"].isin(top_bigrams)][
        ["session_id", "bigram"]
    ]

    # Count (session_id, bigram) -> count
    bgram_counts = (
        bigram_top.groupby(["session_id", "bigram"], sort=False)
        .size()
        .reset_index(name="cnt")
    )

    # Pivot wide
    feat_wide = bgram_counts.pivot(
        index="session_id", columns="bigram", values="cnt"
    ).fillna(0).astype("int32")

    # Safe column names: replace ">" with "_to_"
    feat_wide.columns = [
        "bgram_" + c.replace(">", "_to_") for c in feat_wide.columns
    ]
    feat_wide = feat_wide.reset_index()

    return feat_wide, top_bigrams, global_freq


# ---------------------------------------------------------------------------
# Step 4: assemble full feature matrix
# ---------------------------------------------------------------------------
def build_features(df: pd.DataFrame, sessions: pd.DataFrame,
                   log: logging.Logger) -> tuple[pd.DataFrame, list, list, object]:
    """Build complete session_features_v2 DataFrame."""

    # ---- Top-N template features ---- #
    log.info(f"Selecting top-{TOP_N_TEMPLATES} templates by frequency ...")
    top_tids = (
        df["template_id"].value_counts().head(TOP_N_TEMPLATES).index.tolist()
    )
    df_top = df[df["template_id"].isin(top_tids)][["session_id", "template_id"]]
    tid_counts = (
        df_top.groupby(["session_id", "template_id"], sort=False)
        .size()
        .reset_index(name="cnt")
    )
    tid_wide = tid_counts.pivot(
        index="session_id", columns="template_id", values="cnt"
    ).fillna(0).astype("int32")
    tid_wide.columns = [f"tid_{c}" for c in tid_wide.columns]
    tid_wide = tid_wide.reset_index()
    log.info(f"Template pivot shape: {tid_wide.shape}")

    # ---- Entropy ---- #
    entropy_s = compute_entropy(df, sessions, log)

    # ---- Bigram features ---- #
    bgram_wide, top_bigrams, global_bigram_freq = build_bigram_features(
        df, sessions, log
    )
    log.info(f"Bigram pivot shape: {bgram_wide.shape}")

    # ---- Assemble base ---- #
    feat_df = sessions[["session_id", "dataset", "label", "sequence_length",
                         "unique_template_count"]].copy()

    feat_df["unique_ratio"] = (
        feat_df["unique_template_count"] / feat_df["sequence_length"]
    ).astype("float32")

    feat_df = feat_df.merge(
        entropy_s.reset_index(), on="session_id", how="left"
    )
    feat_df["template_entropy"] = feat_df["template_entropy"].fillna(0).astype("float32")

    # ---- Merge template counts ---- #
    feat_df = feat_df.merge(tid_wide, on="session_id", how="left")
    tid_cols = [c for c in tid_wide.columns if c != "session_id"]
    feat_df[tid_cols] = feat_df[tid_cols].fillna(0).astype("int32")

    # ---- Normalised template frequencies ---- #
    log.info("Normalising template frequency features ...")
    seq_len = feat_df["sequence_length"].values.reshape(-1, 1).astype("float32")
    raw_tid = feat_df[tid_cols].values.astype("float32")
    norm_tid = np.divide(raw_tid, seq_len, where=seq_len > 0,
                         out=np.zeros_like(raw_tid))
    norm_tid_cols = [c + "_norm" for c in tid_cols]
    norm_tid_df = pd.DataFrame(norm_tid, columns=norm_tid_cols, index=feat_df.index)

    # ---- Merge bigram counts ---- #
    bgram_merged = bgram_wide.set_index("session_id").reindex(
        feat_df["session_id"]
    ).fillna(0).astype("int32").reset_index(drop=True)
    bgram_cols = [c for c in bgram_wide.columns if c != "session_id"]

    # ---- Normalised bigram frequencies ---- #
    log.info("Normalising bigram frequency features ...")
    # Denominator for bigrams: sequence_length - 1 (number of transitions)
    n_trans = (feat_df["sequence_length"].values - 1).reshape(-1, 1).astype("float32")
    n_trans = np.where(n_trans <= 0, 1.0, n_trans)   # avoid div-by-zero for len-1 sessions
    raw_bgram = bgram_merged.values.astype("float32")
    norm_bgram = raw_bgram / n_trans
    norm_bgram_cols = [c + "_norm" for c in bgram_cols]
    norm_bgram_df = pd.DataFrame(norm_bgram, columns=norm_bgram_cols, index=feat_df.index)

    # Concatenate all pieces at once to avoid fragmentation
    feat_df = pd.concat(
        [feat_df, norm_tid_df, bgram_merged, norm_bgram_df], axis=1
    )

    # Reset index cleanly after concat
    feat_df = feat_df.reset_index(drop=True)
    log.info(f"Feature matrix shape: {feat_df.shape}")
    return feat_df, top_tids, top_bigrams, global_bigram_freq


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(sessions: pd.DataFrame, feat_df: pd.DataFrame,
                 top_tids: list, top_bigrams: list, global_bigram_freq: object,
                 elapsed: float, peak_mem: float,
                 log: logging.Logger) -> None:

    n_sessions  = len(sessions)
    avg_len     = sessions["sequence_length"].mean()
    med_len     = sessions["sequence_length"].median()
    max_len     = sessions["sequence_length"].max()
    vocab_size  = (
        sessions["ordered_template_sequence"]
        .str.split(",").explode().nunique()
    )
    n_unique_bigrams = len(global_bigram_freq)
    label_dist  = sessions["label"].value_counts().sort_index()
    dataset_dist = sessions["dataset"].value_counts()
    top10 = sessions.nlargest(10, "sequence_length")[
        ["session_id", "dataset", "label", "sequence_length"]
    ]

    # Column summaries for feature report
    tid_raw_cols = [c for c in feat_df.columns
                    if c.startswith("tid_") and not c.endswith("_norm")]
    bgram_raw_cols = [c for c in feat_df.columns
                      if c.startswith("bgram_") and not c.endswith("_norm")]

    lines = [
        "# Stage 23 (V2) Sequence Builder Report",
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
        f"| Unique bigrams (global) | {n_unique_bigrams:,} |",
        f"| Template feature cols (raw+norm) | {len(tid_raw_cols)*2} |",
        f"| Bigram feature cols (raw+norm) | {len(bgram_raw_cols)*2} |",
        f"| Total feature cols | {feat_df.shape[1]} |",
        f"| Execution time | {elapsed:.1f}s |",
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
            f"| {row['session_id']} | {row['dataset']} | "
            f"{row['label']} | {row['sequence_length']:,} |"
        )

    # Top-20 templates (from top_tids list, shown with global count)
    tid_totals = feat_df[tid_raw_cols].sum().sort_values(ascending=False)
    lines += [
        "",
        "---",
        "",
        f"## Top-100 Templates Selected (top 20 shown)",
        "",
        f"Total template columns: {len(tid_raw_cols)} raw + {len(tid_raw_cols)} norm",
        "",
        "| Rank | Column | Total count across sessions |",
        "|-----:|--------|--------------------------:|",
    ]
    for i, (col, cnt) in enumerate(tid_totals.head(20).items(), 1):
        lines.append(f"| {i} | `{col}` | {int(cnt):,} |")

    # Top-20 bigrams
    bgram_totals = feat_df[bgram_raw_cols].sum().sort_values(ascending=False)
    lines += [
        "",
        "---",
        "",
        f"## Top-100 Bigrams Selected (top 20 shown)",
        "",
        f"Total bigram columns: {len(bgram_raw_cols)} raw + {len(bgram_raw_cols)} norm  ",
        f"Total unique bigrams globally: {n_unique_bigrams:,}",
        "",
        "| Rank | Bigram (column) | Total count across sessions |",
        "|-----:|----------------|--------------------------:|",
    ]
    for i, (col, cnt) in enumerate(bgram_totals.head(20).items(), 1):
        lines.append(f"| {i} | `{col}` | {int(cnt):,} |")

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Shape |",
        "|------|-------|",
        f"| `session_sequences_v2.csv` | {n_sessions:,} rows x 6 cols |",
        f"| `session_features_v2.csv`  | {feat_df.shape[0]:,} rows x {feat_df.shape[1]} cols |",
        "",
        "---",
        "",
        "*Stage 23 (v2) completed successfully.*",
    ]

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"Report saved: {REPORT_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log = setup_logging()
    start_time = time.time()

    log.info("=" * 60)
    log.info("Stage 23 V2: Session Sequence Builder (Enhanced)")
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
        feat_df, top_tids, top_bigrams, global_bigram_freq = build_features(
            df, sessions, log
        )
        log.info(f"Memory after features: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to build features: {exc}")
        raise

    # ---- Save outputs ---------------------------------------------------- #
    try:
        SEQ_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Saving session_sequences_v2.csv ({len(sessions):,} rows) ...")
        sessions.to_csv(SEQ_OUTPUT, index=False)

        log.info(
            f"Saving session_features_v2.csv "
            f"({feat_df.shape[0]:,} rows, {feat_df.shape[1]} cols) ..."
        )
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
        write_report(sessions, feat_df, top_tids, top_bigrams,
                     global_bigram_freq, elapsed, peak_mem, log)
    except Exception as exc:
        log.error(f"Failed to write report: {exc}")
        raise

    # ---- Console summary ------------------------------------------------- #
    avg_len = sessions["sequence_length"].mean()
    n_unique_bigrams = len(global_bigram_freq)

    print()
    print("=" * 60)
    print(f"  Total sessions     : {len(sessions):,}")
    print(f"  Avg seq length     : {avg_len:.2f}")
    print(f"  Template vocab     : 7,833")
    print(f"  Unique bigrams     : {n_unique_bigrams:,}")
    print(f"  Feature cols       : {feat_df.shape[1]}")
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
    print("Stage 23 (v2) completed successfully.")


if __name__ == "__main__":
    main()
