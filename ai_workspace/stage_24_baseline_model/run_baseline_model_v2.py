# ai_workspace/stage_24_baseline_model/run_baseline_model_v2.py

"""
Stage 24 V2 - Baseline Anomaly Detection Model (Enhanced)
==========================================================
Uses session_features_v2.csv (404 numeric features incl. bigram + entropy).
Trains IsolationForest(n_estimators=300, random_state=42).

Threshold selection by F1 maximisation:
  - overall_threshold : single threshold maximising F1 across all sessions
  - per-dataset thresholds: separate optimal threshold for hdfs and bgl

Outputs
-------
  data/models/isolation_forest_v2.pkl
  data/intermediate/session_scores_v2.csv
  ai_workspace/reports/stage_24_model_report_v2.md
  ai_workspace/logs/stage_24_baseline_model_v2.log
"""

import logging
import os
import pickle
import sys
import time
import traceback
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE        = Path(__file__).resolve().parents[2]
INPUT_FILE  = BASE / "data/intermediate/session_features_v2.csv"
MODEL_DIR   = BASE / "data/models"
MODEL_FILE  = MODEL_DIR / "isolation_forest_v2.pkl"
SCORES_FILE = BASE / "data/intermediate/session_scores_v2.csv"
REPORT_FILE = BASE / "ai_workspace/reports/stage_24_model_report_v2.md"
LOG_FILE    = BASE / "ai_workspace/logs/stage_24_baseline_model_v2.log"

N_ESTIMATORS  = 300
RANDOM_STATE  = 42
N_THRESHOLDS  = 300   # number of candidate thresholds to evaluate

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
# Threshold optimisation
# ---------------------------------------------------------------------------
def best_f1_threshold(scores: np.ndarray, labels: np.ndarray,
                      n_thresholds: int = N_THRESHOLDS) -> tuple[float, float, dict]:
    """
    Scan `n_thresholds` evenly-spaced candidate thresholds between the
    1st and 99th percentile of `scores`.  Returns:
        (best_threshold, best_f1, metrics_dict)
    Prediction rule: pred = 1 if score >= threshold else 0.
    """
    lo = float(np.percentile(scores, 1))
    hi = float(np.percentile(scores, 99))
    candidates = np.linspace(lo, hi, n_thresholds)

    best_t, best_f1 = candidates[0], -1.0
    for t in candidates:
        pred = (scores >= t).astype("int8")
        f1 = f1_score(labels, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    pred_best = (scores >= best_t).astype("int8")
    metrics = {
        "threshold": float(best_t),
        "f1":        float(best_f1),
        "precision": float(precision_score(labels, pred_best, zero_division=0)),
        "recall":    float(recall_score(labels, pred_best, zero_division=0)),
        "pct_pred":  float(pred_best.mean()),
        "support":   int(labels.sum()),
        "n":         int(len(labels)),
    }
    return best_t, best_f1, metrics


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(n_features: int, train_time: float,
                 scores: np.ndarray, labels: np.ndarray, datasets: np.ndarray,
                 overall_metrics: dict, per_ds_metrics: dict,
                 elapsed: float, peak_mem: float,
                 log: logging.Logger) -> None:

    pred_overall = (scores >= overall_metrics["threshold"]).astype("int8")
    cm = confusion_matrix(labels, pred_overall)
    tn, fp, fn, tp = cm.ravel()
    class_rep = classification_report(labels, pred_overall, zero_division=0)

    lines = [
        "# Stage 24 V2 Baseline Model Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        f"**Peak memory:** {peak_mem:.1f} MB  ",
        "",
        "---",
        "",
        "## Model Configuration",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Model | IsolationForest |",
        f"| n_estimators | {N_ESTIMATORS} |",
        f"| random_state | {RANDOM_STATE} |",
        f"| Feature count | {n_features} |",
        f"| Training sessions | {overall_metrics['n']:,} |",
        f"| Training time | {train_time:.1f}s |",
        f"| Observed anomaly rate | {overall_metrics['support']/overall_metrics['n']:.2%} |",
        "",
        "---",
        "",
        "## Score Distribution",
        "",
        "*(score = -score_samples; higher = more anomalous)*",
        "",
        "| Stat | Value |",
        "|------|------:|",
        f"| Min    | {scores.min():.5f} |",
        f"| p1     | {np.percentile(scores,1):.5f} |",
        f"| Mean   | {scores.mean():.5f} |",
        f"| Median | {np.median(scores):.5f} |",
        f"| p95    | {np.percentile(scores,95):.5f} |",
        f"| p99    | {np.percentile(scores,99):.5f} |",
        f"| Max    | {scores.max():.5f} |",
        "",
        "---",
        "",
        "## Overall Threshold (F1-optimal)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Threshold | {overall_metrics['threshold']:.5f} |",
        f"| F1        | {overall_metrics['f1']:.4f} |",
        f"| Precision | {overall_metrics['precision']:.4f} |",
        f"| Recall    | {overall_metrics['recall']:.4f} |",
        f"| Predicted anomalies | {int(overall_metrics['pct_pred']*overall_metrics['n']):,} ({overall_metrics['pct_pred']:.2%}) |",
        "",
        "**Confusion matrix (pred_overall):**",
        "",
        "| | Pred Normal | Pred Anomaly |",
        "|---|---:|---:|",
        f"| **Actual Normal**  | {tn:,} (TN) | {fp:,} (FP) |",
        f"| **Actual Anomaly** | {fn:,} (FN) | {tp:,} (TP) |",
        "",
        "```",
        class_rep,
        "```",
        "",
        "---",
        "",
        "## Per-Dataset Thresholds (F1-optimal per dataset)",
        "",
        "| Dataset | N | Anomalies | Threshold | F1 | Precision | Recall | Pred Anom % |",
        "|---------|--:|----------:|----------:|---:|----------:|-------:|------------:|",
    ]
    for ds, m in sorted(per_ds_metrics.items()):
        lines.append(
            f"| {ds} | {m['n']:,} | {m['support']:,} ({m['support']/m['n']:.2%}) "
            f"| {m['threshold']:.5f} | {m['f1']:.4f} "
            f"| {m['precision']:.4f} | {m['recall']:.4f} "
            f"| {m['pct_pred']:.2%} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Output Files",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| `isolation_forest_v2.pkl` | Trained IsolationForest (n_estimators=300) |",
        f"| `session_scores_v2.csv` | {overall_metrics['n']:,} rows: session_id, dataset, label, score, pred_overall, pred_by_dataset |",
        "",
        "---",
        "",
        "*Stage 24 (v2) completed successfully.*",
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
    log.info("Stage 24 V2: Baseline Anomaly Detection Model (Enhanced)")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    try:
        # ---- Load -------------------------------------------------------- #
        log.info("Loading session_features_v2.csv ...")
        df = pd.read_csv(INPUT_FILE)
        n_sessions = len(df)
        log.info(f"Loaded {n_sessions:,} sessions.  Memory: {mem_mb():.1f} MB")

        # ---- Feature matrix ---------------------------------------------- #
        exclude = {"session_id", "dataset", "label"}
        feature_cols = [c for c in df.columns if c not in exclude]
        n_features = len(feature_cols)

        X      = df[feature_cols].values.astype("float32")
        y      = df["label"].values.astype("int8")
        ds_arr = df["dataset"].values

        pos_rate = float(y.mean())
        log.info(f"Feature columns : {n_features}")
        log.info(f"Anomaly rate    : {pos_rate:.4f} ({pos_rate:.2%})")
        log.info(f"X shape         : {X.shape}  |  Memory: {mem_mb():.1f} MB")

        # ---- Train ------------------------------------------------------- #
        log.info(
            f"Training IsolationForest "
            f"(n_estimators={N_ESTIMATORS}, random_state={RANDOM_STATE}) ..."
        )
        t0  = time.time()
        clf = IsolationForest(
            n_estimators=N_ESTIMATORS,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        clf.fit(X)
        train_time = time.time() - t0
        log.info(f"Training done in {train_time:.1f}s.  Memory: {mem_mb():.1f} MB")

        # ---- Scores ------------------------------------------------------ #
        log.info("Computing anomaly scores ...")
        scores = (-clf.score_samples(X)).astype("float32")
        log.info(
            f"Score range: [{scores.min():.5f}, {scores.max():.5f}]  "
            f"mean={scores.mean():.5f}  median={float(np.median(scores)):.5f}"
        )

        # ---- Overall F1-optimal threshold -------------------------------- #
        log.info(f"Finding overall F1-optimal threshold ({N_THRESHOLDS} candidates) ...")
        overall_t, overall_f1, overall_metrics = best_f1_threshold(scores, y)
        log.info(
            f"Overall threshold={overall_t:.5f}  "
            f"F1={overall_f1:.4f}  "
            f"P={overall_metrics['precision']:.4f}  "
            f"R={overall_metrics['recall']:.4f}  "
            f"pred_anom={overall_metrics['pct_pred']:.2%}"
        )

        pred_overall = (scores >= overall_t).astype("int8")

        # ---- Per-dataset F1-optimal thresholds --------------------------- #
        log.info("Finding per-dataset F1-optimal thresholds ...")
        datasets = sorted(df["dataset"].unique())
        per_ds_metrics = {}
        ds_thresholds  = {}

        for ds in datasets:
            mask = ds_arr == ds
            t, f1, m = best_f1_threshold(scores[mask], y[mask])
            per_ds_metrics[ds] = m
            ds_thresholds[ds]  = t
            log.info(
                f"  [{ds}] threshold={t:.5f}  F1={f1:.4f}  "
                f"P={m['precision']:.4f}  R={m['recall']:.4f}  "
                f"pred_anom={m['pct_pred']:.2%}"
            )

        # Apply per-dataset threshold
        pred_by_dataset = np.zeros(n_sessions, dtype="int8")
        for ds, t in ds_thresholds.items():
            mask = ds_arr == ds
            pred_by_dataset[mask] = (scores[mask] >= t).astype("int8")

        log.info(
            f"pred_by_dataset anomalies: "
            f"{pred_by_dataset.sum():,} ({pred_by_dataset.mean():.2%})"
        )

        # ---- Save model -------------------------------------------------- #
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as fh:
            pickle.dump(clf, fh, protocol=pickle.HIGHEST_PROTOCOL)
        model_kb = MODEL_FILE.stat().st_size / 1024
        log.info(f"Model saved: {MODEL_FILE}  ({model_kb:.1f} KB)")

        # ---- Save scores ------------------------------------------------- #
        scores_df = pd.DataFrame({
            "session_id":      df["session_id"],
            "dataset":         df["dataset"],
            "label":           y,
            "score":           scores,
            "pred_overall":    pred_overall,
            "pred_by_dataset": pred_by_dataset,
        })
        SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
        scores_df.to_csv(SCORES_FILE, index=False)
        log.info(f"Scores saved: {SCORES_FILE}  ({len(scores_df):,} rows)")

        elapsed  = time.time() - start_time
        peak_mem = mem_mb()
        log.info(f"Total elapsed: {elapsed:.1f}s  |  Peak memory: {peak_mem:.1f} MB")

        # ---- Report ------------------------------------------------------ #
        write_report(
            n_features, train_time, scores, y, ds_arr,
            overall_metrics, per_ds_metrics, elapsed, peak_mem, log,
        )

    except Exception:
        print(traceback.format_exc())
        sys.exit(1)

    # ---- Console summary ------------------------------------------------- #
    print()
    print("=" * 60)
    print(f"  Sessions        : {n_sessions:,}")
    print(f"  Features        : {n_features}")
    print(f"  Train time      : {train_time:.1f}s")
    print()
    print(f"  Overall threshold (F1-opt) : {overall_t:.5f}")
    print(f"    F1 / P / R    : {overall_metrics['f1']:.4f} / "
          f"{overall_metrics['precision']:.4f} / {overall_metrics['recall']:.4f}")
    print(f"    Pred anomalies: {pred_overall.sum():,} ({pred_overall.mean():.2%})")
    print()
    print("  Per-dataset thresholds:")
    for ds, m in sorted(per_ds_metrics.items()):
        print(f"    {ds:6s}  t={m['threshold']:.5f}  "
              f"F1={m['f1']:.4f}  P={m['precision']:.4f}  R={m['recall']:.4f}")
    print()
    print("  Generated files:")
    for f in [MODEL_FILE, SCORES_FILE, REPORT_FILE, LOG_FILE,
              Path(__file__)]:
        print(f"    {f}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s   |   Peak mem: {peak_mem:.1f} MB")
    print("=" * 60)
    print()
    print("Stage 24 (v2) completed successfully.")


if __name__ == "__main__":
    main()
