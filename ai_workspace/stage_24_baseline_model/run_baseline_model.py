# ai_workspace/stage_24_baseline_model/run_baseline_model.py

"""
Stage 24 - Baseline Anomaly Detection Model
=============================================
Trains an IsolationForest on session-level features, selects the best
contamination value by PR-AUC, saves the model and per-session scores.

Inputs
------
  data/intermediate/session_features.csv

Outputs
-------
  data/models/isolation_forest.pkl
  data/intermediate/session_scores.csv
  ai_workspace/reports/stage_24_model_report.md
  ai_workspace/logs/stage_24_baseline_model.log
"""

import logging
import os
import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE         = Path(__file__).resolve().parents[2]
INPUT_FILE   = BASE / "data/intermediate/session_features.csv"
MODEL_DIR    = BASE / "data/models"
MODEL_FILE   = MODEL_DIR / "isolation_forest.pkl"
SCORES_FILE  = BASE / "data/intermediate/session_scores.csv"
REPORT_FILE  = BASE / "ai_workspace/reports/stage_24_model_report.md"
LOG_FILE     = BASE / "ai_workspace/logs/stage_24_baseline_model.log"

CONTAMINATION_CANDIDATES = [0.05, 0.10, 0.20]
N_ESTIMATORS             = 200
RANDOM_STATE             = 42

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
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log = setup_logging()
    start_time = time.time()

    log.info("=" * 60)
    log.info("Stage 24: Baseline Anomaly Detection Model")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    # ---- Load ------------------------------------------------------------ #
    try:
        log.info("Loading session_features.csv ...")
        df = pd.read_csv(INPUT_FILE)
        n_sessions = len(df)
        log.info(f"Loaded {n_sessions:,} sessions.  Memory: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to load input: {exc}")
        raise

    # ---- Build feature matrix -------------------------------------------- #
    try:
        exclude_cols = {"session_id", "dataset", "label"}
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        n_features = len(feature_cols)

        X = df[feature_cols].values.astype("float32")
        y = df["label"].values.astype("int8")

        pos_rate = y.mean()
        log.info(f"Feature columns: {n_features}")
        log.info(f"Positive (anomaly) rate: {pos_rate:.4f} ({pos_rate:.2%})")
        log.info(f"X shape: {X.shape}  |  Memory: {mem_mb():.1f} MB")
    except Exception as exc:
        log.error(f"Failed to build feature matrix: {exc}")
        raise

    # ---- Contamination sweep --------------------------------------------- #
    try:
        log.info(
            f"Sweeping contamination candidates: {CONTAMINATION_CANDIDATES}"
        )
        sweep_results = []
        for cont in CONTAMINATION_CANDIDATES:
            t0 = time.time()
            clf = IsolationForest(
                n_estimators=N_ESTIMATORS,
                contamination=cont,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            clf.fit(X)
            # score_samples returns higher = more normal; negate for anomaly score
            raw_scores = clf.score_samples(X)          # shape (n,)
            anom_scores = -raw_scores                  # higher = more anomalous
            pr_auc = average_precision_score(y, anom_scores)
            elapsed_c = time.time() - t0
            log.info(
                f"  contamination={cont:.2f}  PR-AUC={pr_auc:.4f}  "
                f"time={elapsed_c:.1f}s"
            )
            sweep_results.append({
                "contamination": cont,
                "pr_auc": pr_auc,
                "elapsed": elapsed_c,
                "clf": clf,
                "anom_scores": anom_scores,
            })
    except Exception as exc:
        log.error(f"Contamination sweep failed: {exc}")
        raise

    # ---- Select best contamination --------------------------------------- #
    try:
        best = max(sweep_results, key=lambda r: r["pr_auc"])
        best_cont   = best["contamination"]
        best_pr_auc = best["pr_auc"]
        best_clf    = best["clf"]
        best_scores = best["anom_scores"]
        train_time  = sum(r["elapsed"] for r in sweep_results)

        log.info(
            f"Best contamination: {best_cont:.2f}  PR-AUC={best_pr_auc:.4f}"
        )
    except Exception as exc:
        log.error(f"Failed to select best model: {exc}")
        raise

    # ---- Generate predictions -------------------------------------------- #
    try:
        # predict() returns +1 (normal) / -1 (anomaly)
        raw_pred = best_clf.predict(X)
        pred = (raw_pred == -1).astype("int8")   # 1 = anomaly, 0 = normal

        pct_predicted_anom = pred.mean()
        log.info(
            f"Predicted anomalies: {pred.sum():,} / {n_sessions:,} "
            f"({pct_predicted_anom:.2%})"
        )
    except Exception as exc:
        log.error(f"Failed to generate predictions: {exc}")
        raise

    # ---- Sanity metrics -------------------------------------------------- #
    try:
        precision = precision_score(y, pred, zero_division=0)
        recall    = recall_score(y, pred, zero_division=0)
        f1        = f1_score(y, pred, zero_division=0)
        log.info(
            f"Sanity metrics vs labels  |  "
            f"Precision={precision:.4f}  Recall={recall:.4f}  F1={f1:.4f}"
        )
        class_report = classification_report(y, pred, zero_division=0)
        log.info("Classification report:\n" + class_report)
    except Exception as exc:
        log.error(f"Failed to compute sanity metrics: {exc}")
        raise

    # ---- Score distribution ---------------------------------------------- #
    score_min    = float(best_scores.min())
    score_mean   = float(best_scores.mean())
    score_median = float(np.median(best_scores))
    score_max    = float(best_scores.max())
    score_p95    = float(np.percentile(best_scores, 95))
    log.info(
        f"Score distribution  min={score_min:.4f}  mean={score_mean:.4f}  "
        f"median={score_median:.4f}  p95={score_p95:.4f}  max={score_max:.4f}"
    )

    # ---- Save model ------------------------------------------------------ #
    try:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as fh:
            pickle.dump(best_clf, fh, protocol=pickle.HIGHEST_PROTOCOL)
        model_kb = MODEL_FILE.stat().st_size / 1024
        log.info(f"Model saved: {MODEL_FILE}  ({model_kb:.1f} KB)")
    except Exception as exc:
        log.error(f"Failed to save model: {exc}")
        raise

    # ---- Save scores file ------------------------------------------------ #
    try:
        scores_df = pd.DataFrame({
            "session_id": df["session_id"],
            "dataset":    df["dataset"],
            "label":      y,
            "score":      best_scores.astype("float32"),
            "pred":       pred,
        })
        SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
        scores_df.to_csv(SCORES_FILE, index=False)
        log.info(f"Scores saved: {SCORES_FILE}  ({len(scores_df):,} rows)")
    except Exception as exc:
        log.error(f"Failed to save scores: {exc}")
        raise

    elapsed  = time.time() - start_time
    peak_mem = mem_mb()
    log.info(f"Total elapsed: {elapsed:.1f}s  |  Peak memory: {peak_mem:.1f} MB")

    # ---- Write report ---------------------------------------------------- #
    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

        sweep_rows = "\n".join(
            f"| {r['contamination']:.2f} | {r['pr_auc']:.4f} | {r['elapsed']:.1f}s |"
            + (" **chosen** |" if r['contamination'] == best_cont else " |")
            for r in sweep_results
        )

        lines = [
            "# Stage 24 Baseline Model Report",
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
            f"| Chosen contamination | {best_cont:.2f} |",
            f"| Feature count | {n_features} |",
            f"| Training sessions | {n_sessions:,} |",
            f"| Observed anomaly rate | {pos_rate:.2%} |",
            "",
            "---",
            "",
            "## Contamination Sweep",
            "",
            "Contamination selected by highest PR-AUC (average precision score)  ",
            "against ground-truth labels. This is for selection only — the model  ",
            "is fully unsupervised during training.",
            "",
            "| Contamination | PR-AUC | Train time | |",
            "|--------------|-------:|-----------|---|",
        ]
        for r in sweep_results:
            chosen_tag = " **chosen**" if r["contamination"] == best_cont else ""
            lines.append(
                f"| {r['contamination']:.2f} | {r['pr_auc']:.4f} "
                f"| {r['elapsed']:.1f}s |{chosen_tag} |"
            )

        lines += [
            "",
            "---",
            "",
            "## Score Distribution",
            "",
            "*(Anomaly score = -score_samples; higher = more anomalous)*",
            "",
            "| Stat | Value |",
            "|------|------:|",
            f"| Min | {score_min:.4f} |",
            f"| Mean | {score_mean:.4f} |",
            f"| Median | {score_median:.4f} |",
            f"| 95th pct | {score_p95:.4f} |",
            f"| Max | {score_max:.4f} |",
            "",
            "---",
            "",
            "## Predictions Summary",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Total sessions | {n_sessions:,} |",
            f"| Predicted anomalies | {pred.sum():,} ({pct_predicted_anom:.2%}) |",
            f"| Actual anomalies (label=1) | {y.sum():,} ({pos_rate:.2%}) |",
            "",
            "---",
            "",
            "## Sanity Metrics (pred vs label)",
            "",
            "*(Unsupervised model — labels used only for evaluation, not training)*",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Precision | {precision:.4f} |",
            f"| Recall | {recall:.4f} |",
            f"| F1 | {f1:.4f} |",
            f"| PR-AUC (best) | {best_pr_auc:.4f} |",
            "",
            "```",
            class_report,
            "```",
            "",
            "---",
            "",
            "## Output Files",
            "",
            "| File | Description |",
            "|------|-------------|",
            f"| `isolation_forest.pkl` | Trained IsolationForest model |",
            f"| `session_scores.csv` | Per-session anomaly scores and predictions ({n_sessions:,} rows) |",
            "",
            "---",
            "",
            "*Stage 24 completed successfully.*",
        ]

        REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info(f"Report saved: {REPORT_FILE}")
    except Exception as exc:
        log.error(f"Failed to write report: {exc}")
        raise

    # ---- Console summary ------------------------------------------------- #
    print()
    print("=" * 60)
    print(f"  Sessions          : {n_sessions:,}")
    print(f"  Features          : {n_features}")
    print(f"  Best contamination: {best_cont:.2f}  (PR-AUC={best_pr_auc:.4f})")
    print(f"  Predicted anomaly : {pct_predicted_anom:.2%}")
    print(f"  Precision/Recall/F1: {precision:.3f} / {recall:.3f} / {f1:.3f}")
    print()
    print("  Contamination sweep:")
    for r in sweep_results:
        tag = " <-- chosen" if r["contamination"] == best_cont else ""
        print(f"    {r['contamination']:.2f}  PR-AUC={r['pr_auc']:.4f}{tag}")
    print()
    print("  Generated files:")
    print(f"    {MODEL_FILE}")
    print(f"    {SCORES_FILE}")
    print(f"    {REPORT_FILE}")
    print(f"    {LOG_FILE}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s   |   Peak mem: {peak_mem:.1f} MB")
    print("=" * 60)
    print()
    print("Stage 24 completed successfully.")


if __name__ == "__main__":
    main()
