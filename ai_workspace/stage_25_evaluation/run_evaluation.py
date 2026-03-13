# ai_workspace/stage_25_evaluation/run_evaluation.py

"""
Stage 25 - Model Evaluation
=============================
Loads session_scores.csv (produced by Stage 24) and computes full
evaluation metrics plus publication-ready plots.

No model retraining; no feature computation. Read-only on input data.

Outputs
-------
  ai_workspace/stage_25_evaluation/roc_curve.png
  ai_workspace/stage_25_evaluation/pr_curve.png
  ai_workspace/stage_25_evaluation/score_histogram.png
  ai_workspace/stage_25_evaluation/confusion_matrix.png
  ai_workspace/reports/stage_25_evaluation_report.md
  ai_workspace/logs/stage_25_evaluation.log
"""

import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")           # non-interactive backend for file output
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE       = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE / "data/intermediate/session_scores.csv"
PLOT_DIR   = BASE / "ai_workspace/stage_25_evaluation"
REPORT_FILE = BASE / "ai_workspace/reports/stage_25_evaluation_report.md"
LOG_FILE   = BASE / "ai_workspace/logs/stage_25_evaluation.log"

# ---------------------------------------------------------------------------
# Logging
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


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def compute_metrics(y_true: np.ndarray, y_score: np.ndarray,
                    y_pred: np.ndarray) -> dict:
    return {
        "roc_auc":   roc_auc_score(y_true, y_score),
        "pr_auc":    average_precision_score(y_true, y_score),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall":    recall_score(y_true, y_pred, zero_division=0),
        "f1":        f1_score(y_true, y_pred, zero_division=0),
        "support":   int(y_true.sum()),
        "n":         len(y_true),
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_roc(y_true, y_score, path: Path, log: logging.Logger) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    auc = roc_auc_score(y_true, y_score)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, lw=1.5, label=f"ROC AUC = {auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — IsolationForest Baseline")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path}")


def plot_pr(y_true, y_score, path: Path, log: logging.Logger) -> None:
    prec, rec, _ = precision_recall_curve(y_true, y_score)
    ap = average_precision_score(y_true, y_score)
    baseline = y_true.mean()

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec, lw=1.5, label=f"PR AUC = {ap:.4f}")
    ax.axhline(baseline, color="gray", ls="--", lw=0.8,
               label=f"Random baseline ({baseline:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve — IsolationForest Baseline")
    ax.legend(loc="upper right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path}")


def plot_score_histogram(df: pd.DataFrame, path: Path,
                         log: logging.Logger) -> None:
    normal = df.loc[df["label"] == 0, "score"].values
    anomaly = df.loc[df["label"] == 1, "score"].values

    # Use same bin edges for both classes
    all_vals = np.concatenate([normal, anomaly])
    bins = np.linspace(all_vals.min(), all_vals.max(), 60)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(normal,  bins=bins, alpha=0.6, label=f"Normal (n={len(normal):,})",
            color="steelblue", density=True)
    ax.hist(anomaly, bins=bins, alpha=0.6, label=f"Anomaly (n={len(anomaly):,})",
            color="tomato", density=True)
    ax.set_xlabel("Anomaly Score (-score_samples)")
    ax.set_ylabel("Density")
    ax.set_title("Score Distribution by Label")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path}")


def plot_confusion(y_true, y_pred, path: Path, log: logging.Logger) -> None:
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=["Normal (0)", "Anomaly (1)"],
    )
    fig, ax = plt.subplots(figsize=(5, 4))
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title("Confusion Matrix — IsolationForest Baseline")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(overall: dict, per_ds: dict,
                 cm: np.ndarray, df: pd.DataFrame,
                 elapsed: float, log: logging.Logger) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    n_sessions   = overall["n"]
    pos_rate     = overall["support"] / n_sessions
    pred_anom    = int(df["pred"].sum())
    score_min    = float(df["score"].min())
    score_mean   = float(df["score"].mean())
    score_median = float(df["score"].median())
    score_max    = float(df["score"].max())

    plot_dir_rel = "../../ai_workspace/stage_25_evaluation"

    lines = [
        "# Stage 25 Evaluation Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        "",
        "---",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Sessions evaluated | {n_sessions:,} |",
        f"| Actual anomalies | {overall['support']:,} ({pos_rate:.2%}) |",
        f"| Predicted anomalies | {pred_anom:,} ({pred_anom/n_sessions:.2%}) |",
        f"| ROC AUC | {overall['roc_auc']:.4f} |",
        f"| PR AUC | {overall['pr_auc']:.4f} |",
        f"| Precision | {overall['precision']:.4f} |",
        f"| Recall | {overall['recall']:.4f} |",
        f"| F1 | {overall['f1']:.4f} |",
        "",
        "---",
        "",
        "## Per-Dataset Metrics",
        "",
        "| Dataset | N | Anomalies | ROC AUC | PR AUC | Precision | Recall | F1 |",
        "|---------|--:|----------:|--------:|-------:|----------:|-------:|---:|",
    ]
    for ds, m in sorted(per_ds.items()):
        lines.append(
            f"| {ds} | {m['n']:,} | {m['support']:,} ({m['support']/m['n']:.2%}) "
            f"| {m['roc_auc']:.4f} | {m['pr_auc']:.4f} "
            f"| {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} |"
        )

    tn, fp, fn, tp = cm.ravel()
    lines += [
        "",
        "---",
        "",
        "## Confusion Matrix",
        "",
        "| | Predicted Normal | Predicted Anomaly |",
        "|---|----------------:|------------------:|",
        f"| **Actual Normal**  | {tn:,} (TN) | {fp:,} (FP) |",
        f"| **Actual Anomaly** | {fn:,} (FN) | {tp:,} (TP) |",
        "",
        "---",
        "",
        "## Score Distribution",
        "",
        "| Stat | Value |",
        "|------|------:|",
        f"| Min  | {score_min:.4f} |",
        f"| Mean | {score_mean:.4f} |",
        f"| Median | {score_median:.4f} |",
        f"| Max  | {score_max:.4f} |",
        "",
        "---",
        "",
        "## Notes",
        "",
        "**Class imbalance:** The dataset is imbalanced (~19% anomalies at session level). "
        "PR AUC is a more informative metric than ROC AUC under imbalance, since it "
        "penalises false positives relative to the minority class.",
        "",
        "**Contamination choice:** All three contamination candidates (0.05, 0.10, 0.20) "
        "yielded identical PR-AUC (0.2518) because `average_precision_score` is computed "
        "from continuous `score_samples`, which are independent of the contamination "
        "threshold. Contamination 0.05 was selected (lowest/first). The low F1 reflects "
        "that IsolationForest, an unsupervised method, cannot fully separate the anomaly "
        "distribution given the aggregate feature space used here.",
        "",
        "**Interpretation:** ROC AUC > 0.5 confirms the model has learned a signal, but "
        "low recall shows many anomalous sessions are scored close to normal ones — "
        "consistent with the narrow score range observed (0.30–0.49).",
        "",
        "---",
        "",
        "## Generated Plots",
        "",
        "| Plot | File |",
        "|------|------|",
        "| ROC Curve | `ai_workspace/stage_25_evaluation/roc_curve.png` |",
        "| PR Curve | `ai_workspace/stage_25_evaluation/pr_curve.png` |",
        "| Score Histogram | `ai_workspace/stage_25_evaluation/score_histogram.png` |",
        "| Confusion Matrix | `ai_workspace/stage_25_evaluation/confusion_matrix.png` |",
        "",
        "---",
        "",
        "*Stage 25 completed successfully.*",
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
    log.info("Stage 25: Model Evaluation")
    log.info(f"Input  : {INPUT_FILE}")
    log.info("=" * 60)

    # ---- Load ------------------------------------------------------------ #
    try:
        log.info("Loading session_scores.csv ...")
        df = pd.read_csv(
            INPUT_FILE,
            dtype={"label": "int8", "pred": "int8", "score": "float32"},
        )
        log.info(f"Loaded {len(df):,} rows.")
    except Exception as exc:
        log.error(f"Failed to load input: {exc}")
        raise

    y_true  = df["label"].values.astype("int8")
    y_score = df["score"].values.astype("float64")
    y_pred  = df["pred"].values.astype("int8")

    # ---- Overall metrics ------------------------------------------------- #
    try:
        log.info("Computing overall metrics ...")
        overall = compute_metrics(y_true, y_score, y_pred)
        log.info(
            f"  ROC AUC={overall['roc_auc']:.4f}  "
            f"PR AUC={overall['pr_auc']:.4f}  "
            f"Precision={overall['precision']:.4f}  "
            f"Recall={overall['recall']:.4f}  "
            f"F1={overall['f1']:.4f}"
        )
    except Exception as exc:
        log.error(f"Failed to compute overall metrics: {exc}")
        raise

    # ---- Confusion matrix ------------------------------------------------ #
    try:
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        log.info(f"Confusion matrix  TN={tn:,}  FP={fp:,}  FN={fn:,}  TP={tp:,}")
    except Exception as exc:
        log.error(f"Failed to compute confusion matrix: {exc}")
        raise

    # ---- Per-dataset metrics --------------------------------------------- #
    try:
        log.info("Computing per-dataset metrics ...")
        per_ds = {}
        for ds, grp in df.groupby("dataset"):
            yt  = grp["label"].values.astype("int8")
            ys  = grp["score"].values.astype("float64")
            yp  = grp["pred"].values.astype("int8")
            per_ds[ds] = compute_metrics(yt, ys, yp)
            log.info(
                f"  [{ds}]  n={per_ds[ds]['n']:,}  "
                f"ROC={per_ds[ds]['roc_auc']:.4f}  "
                f"PR={per_ds[ds]['pr_auc']:.4f}  "
                f"F1={per_ds[ds]['f1']:.4f}"
            )
    except Exception as exc:
        log.error(f"Failed to compute per-dataset metrics: {exc}")
        raise

    # ---- Plots ----------------------------------------------------------- #
    try:
        PLOT_DIR.mkdir(parents=True, exist_ok=True)
        log.info("Generating plots ...")

        plot_roc(y_true, y_score, PLOT_DIR / "roc_curve.png", log)
        plot_pr(y_true, y_score, PLOT_DIR / "pr_curve.png", log)
        plot_score_histogram(df, PLOT_DIR / "score_histogram.png", log)
        plot_confusion(y_true, y_pred, PLOT_DIR / "confusion_matrix.png", log)
    except Exception as exc:
        log.error(f"Failed to generate plots: {exc}")
        raise

    elapsed = time.time() - start_time
    log.info(f"Total elapsed: {elapsed:.1f}s")

    # ---- Report ---------------------------------------------------------- #
    try:
        write_report(overall, per_ds, cm, df, elapsed, log)
    except Exception as exc:
        log.error(f"Failed to write report: {exc}")
        raise

    # ---- Console summary ------------------------------------------------- #
    generated = [
        PLOT_DIR / "roc_curve.png",
        PLOT_DIR / "pr_curve.png",
        PLOT_DIR / "score_histogram.png",
        PLOT_DIR / "confusion_matrix.png",
        REPORT_FILE,
        LOG_FILE,
        Path(__file__),
    ]

    print()
    print("=" * 60)
    print(f"  Sessions evaluated : {len(df):,}")
    print(f"  ROC AUC            : {overall['roc_auc']:.4f}")
    print(f"  PR AUC             : {overall['pr_auc']:.4f}")
    print(f"  Precision / Recall / F1 : "
          f"{overall['precision']:.3f} / {overall['recall']:.3f} / {overall['f1']:.3f}")
    print()
    print("  Per-dataset summary:")
    for ds, m in sorted(per_ds.items()):
        print(f"    {ds:6s}  ROC={m['roc_auc']:.4f}  PR={m['pr_auc']:.4f}  F1={m['f1']:.4f}")
    print()
    print("  Generated files:")
    for f in generated:
        print(f"    {f}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s")
    print("=" * 60)
    print()
    print("Stage 25 completed successfully.")


if __name__ == "__main__":
    main()
