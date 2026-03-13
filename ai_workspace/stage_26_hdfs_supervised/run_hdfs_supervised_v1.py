# ai_workspace/stage_26_hdfs_supervised/run_hdfs_supervised_v1.py

"""
Stage 26 - HDFS Supervised Baseline
=====================================
Trains a LogisticRegression classifier on HDFS sessions only,
using v2 session features (404 numeric cols) and ground-truth labels.

Split: 80% train / 10% val / 10% test  (stratified, random_state=42)
Pipeline: StandardScaler -> LogisticRegression(class_weight="balanced")

Threshold choices:
  pred_0_5     : standard 0.5 cutoff
  pred_bestF1  : threshold that maximises F1 on validation set

Outputs
-------
  data/models/hdfs_logreg_v1.pkl
  data/intermediate/hdfs_supervised_scores_v1.csv
  ai_workspace/reports/stage_26_hdfs_supervised_report_v1.md
  ai_workspace/logs/stage_26_hdfs_supervised_v1.log
  ai_workspace/stage_26_hdfs_supervised/roc_curve_hdfs_v1.png
  ai_workspace/stage_26_hdfs_supervised/pr_curve_hdfs_v1.png
  ai_workspace/stage_26_hdfs_supervised/confusion_hdfs_v1.png
"""

import logging
import os
import pickle
import sys
import time
import traceback
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psutil
from sklearn.linear_model import LogisticRegression
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
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE        = Path(__file__).resolve().parents[2]
INPUT_FILE  = BASE / "data/intermediate/session_features_v2.csv"
MODEL_DIR   = BASE / "data/models"
MODEL_FILE  = MODEL_DIR / "hdfs_logreg_v1.pkl"
SCORES_FILE = BASE / "data/intermediate/hdfs_supervised_scores_v1.csv"
REPORT_FILE = BASE / "ai_workspace/reports/stage_26_hdfs_supervised_report_v1.md"
LOG_FILE    = BASE / "ai_workspace/logs/stage_26_hdfs_supervised_v1.log"
PLOT_DIR    = BASE / "ai_workspace/stage_26_hdfs_supervised"

RANDOM_STATE = 42
VAL_SIZE     = 0.10
TEST_SIZE    = 0.10
N_THRESH     = 300

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
# Threshold helpers
# ---------------------------------------------------------------------------
def best_f1_threshold(proba: np.ndarray, y: np.ndarray,
                      n: int = N_THRESH) -> tuple[float, dict]:
    lo, hi = float(np.percentile(proba, 1)), float(np.percentile(proba, 99))
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(lo, hi, n):
        f1 = f1_score(y, (proba >= t).astype("int8"), zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, float(t)
    pred = (proba >= best_t).astype("int8")
    return best_t, _metrics(y, proba, pred)


def _metrics(y_true, proba, pred) -> dict:
    cm = confusion_matrix(y_true, pred)
    tn, fp, fn, tp = cm.ravel()
    return {
        "roc_auc":   roc_auc_score(y_true, proba),
        "pr_auc":    average_precision_score(y_true, proba),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall":    recall_score(y_true, pred, zero_division=0),
        "f1":        f1_score(y_true, pred, zero_division=0),
        "pct_pred":  float(pred.mean()),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "n":  int(len(y_true)),
        "support": int(y_true.sum()),
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_roc(y_test, proba_test, path: Path, log) -> None:
    fpr, tpr, _ = roc_curve(y_test, proba_test)
    auc = roc_auc_score(y_test, proba_test)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, lw=1.5, color="steelblue", label=f"ROC AUC = {auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — HDFS LogReg V1 (test set)")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path.name}")


def plot_pr(y_test, proba_test, path: Path, log) -> None:
    prec, rec, _ = precision_recall_curve(y_test, proba_test)
    ap = average_precision_score(y_test, proba_test)
    baseline = float(y_test.mean())
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec, lw=1.5, color="steelblue", label=f"PR AUC = {ap:.4f}")
    ax.axhline(baseline, color="gray", ls="--", lw=0.8,
               label=f"Random ({baseline:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("PR Curve — HDFS LogReg V1 (test set)")
    ax.legend(loc="upper right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path.name}")


def plot_confusion(y_test, pred_05, pred_best, path: Path, log) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    labels = ["Normal", "Anomaly"]
    for ax, pred, title in zip(
        axes,
        [pred_05, pred_best],
        ["threshold=0.5", "threshold=bestF1"],
    ):
        cm = confusion_matrix(y_test, pred)
        disp = ConfusionMatrixDisplay(cm, display_labels=labels)
        disp.plot(ax=ax, colorbar=False, cmap="Blues")
        ax.set_title(title)
    fig.suptitle("Confusion Matrices — HDFS LogReg V1 (test set)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {path.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(sizes: dict, anomaly_rate: float,
                 val_t05: dict, val_best: dict, best_thresh: float,
                 test_t05: dict, test_best: dict,
                 elapsed: float, peak_mem: float,
                 log) -> None:

    def mrow(label, m):
        return (
            f"| {label} | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} "
            f"| {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} "
            f"| {m['pct_pred']:.2%} |"
        )

    def cm_block(title, m):
        return [
            f"**{title}**",
            "",
            "| | Pred Normal | Pred Anomaly |",
            "|---|---:|---:|",
            f"| **Actual Normal**  | {m['tn']:,} (TN) | {m['fp']:,} (FP) |",
            f"| **Actual Anomaly** | {m['fn']:,} (FN) | {m['tp']:,} (TP) |",
            "",
        ]

    lines = [
        "# Stage 26 HDFS Supervised Baseline Report",
        "",
        f"**Generated:** {date.today()}  ",
        f"**Execution time:** {elapsed:.1f}s  ",
        f"**Peak memory:** {peak_mem:.1f} MB  ",
        "",
        "---",
        "",
        "## Dataset",
        "",
        "| Split | Rows | Anomalies | Anomaly Rate |",
        "|-------|-----:|----------:|-------------:|",
        f"| Train | {sizes['train']:,} | {sizes['train_pos']:,} | {sizes['train_pos']/sizes['train']:.2%} |",
        f"| Val   | {sizes['val']:,}   | {sizes['val_pos']:,}   | {sizes['val_pos']/sizes['val']:.2%} |",
        f"| Test  | {sizes['test']:,}  | {sizes['test_pos']:,}  | {sizes['test_pos']/sizes['test']:.2%} |",
        f"| **Total HDFS** | {sizes['total']:,} | {sizes['total_pos']:,} | {anomaly_rate:.2%} |",
        "",
        "---",
        "",
        "## Model",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        "| Algorithm | LogisticRegression |",
        "| Scaler | StandardScaler (fit on train) |",
        "| max_iter | 2000 |",
        "| class_weight | balanced |",
        "| Features | 404 numeric cols |",
        f"| Best F1 threshold (from val) | {best_thresh:.5f} |",
        "",
        "---",
        "",
        "## Validation Metrics",
        "",
        "| Threshold | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anom% |",
        "|-----------|--------:|-------:|----------:|-------:|---:|-----------:|",
        mrow("0.5", val_t05),
        mrow(f"bestF1={best_thresh:.4f}", val_best),
        "",
        "---",
        "",
        "## Test Metrics",
        "",
        "| Threshold | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anom% |",
        "|-----------|--------:|-------:|----------:|-------:|---:|-----------:|",
        mrow("0.5", test_t05),
        mrow(f"bestF1={best_thresh:.4f}", test_best),
        "",
        "---",
        "",
        "## Confusion Matrices (test set)",
        "",
    ]
    lines += cm_block("Threshold = 0.5",         test_t05)
    lines += cm_block(f"Threshold = bestF1 ({best_thresh:.5f})", test_best)

    lines += [
        "---",
        "",
        "## Generated Plots",
        "",
        "| Plot | File |",
        "|------|------|",
        "| ROC Curve | `ai_workspace/stage_26_hdfs_supervised/roc_curve_hdfs_v1.png` |",
        "| PR Curve  | `ai_workspace/stage_26_hdfs_supervised/pr_curve_hdfs_v1.png` |",
        "| Confusion | `ai_workspace/stage_26_hdfs_supervised/confusion_hdfs_v1.png` |",
        "",
        "---",
        "",
        "*Stage 26 (HDFS supervised) completed successfully.*",
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
    log.info("Stage 26: HDFS Supervised Baseline (LogisticRegression)")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    try:
        # ---- Load & filter ------------------------------------------------ #
        log.info("Loading session_features_v2.csv (HDFS rows only) ...")
        df_full = pd.read_csv(INPUT_FILE)
        df = df_full[df_full["dataset"] == "hdfs"].reset_index(drop=True)
        n_hdfs = len(df)
        log.info(f"HDFS sessions: {n_hdfs:,}  Memory: {mem_mb():.1f} MB")

        exclude = {"session_id", "dataset", "label"}
        feat_cols = [c for c in df.columns if c not in exclude]
        n_features = len(feat_cols)

        X = df[feat_cols].values.astype("float32")
        y = df["label"].values.astype("int8")
        # Use integer indices for splitting; extract IDs afterwards to avoid
        # pyarrow-backed string array incompatibility with sklearn splitters.
        idx = np.arange(n_hdfs)

        anomaly_rate = float(y.mean())
        log.info(f"Features: {n_features}  |  Anomaly rate: {anomaly_rate:.4f} ({anomaly_rate:.2%})")

        # ---- Split: 80 / 10 / 10 ----------------------------------------- #
        # First: 80% train, 20% temp
        idx_train, idx_temp, y_train, y_temp = train_test_split(
            idx, y, test_size=VAL_SIZE + TEST_SIZE,
            stratify=y, random_state=RANDOM_STATE,
        )
        # Then: split temp into 50/50 -> val 10%, test 10%
        idx_val, idx_test, y_val, y_test = train_test_split(
            idx_temp, y_temp,
            test_size=0.5, stratify=y_temp, random_state=RANDOM_STATE,
        )

        X_train = X[idx_train]
        X_val   = X[idx_val]
        X_test  = X[idx_test]
        ids_all = df["session_id"].tolist()  # plain Python list, index-safe

        sizes = {
            "train": len(y_train), "train_pos": int(y_train.sum()),
            "val":   len(y_val),   "val_pos":   int(y_val.sum()),
            "test":  len(y_test),  "test_pos":  int(y_test.sum()),
            "total": n_hdfs,       "total_pos": int(y.sum()),
        }
        log.info(
            f"Split -> train={sizes['train']:,} ({sizes['train_pos']:,} anom)  "
            f"val={sizes['val']:,} ({sizes['val_pos']:,} anom)  "
            f"test={sizes['test']:,} ({sizes['test_pos']:,} anom)"
        )

        # ---- Pipeline: scaler + logistic regression ----------------------- #
        log.info("Building Pipeline: StandardScaler + LogisticRegression ...")
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                solver="lbfgs",
            )),
        ])

        log.info("Fitting pipeline on train set ...")
        t0 = time.time()
        pipe.fit(X_train, y_train)
        train_time = time.time() - t0
        log.info(f"Training done in {train_time:.1f}s.  Memory: {mem_mb():.1f} MB")

        # ---- Probabilities ------------------------------------------------ #
        log.info("Computing probabilities on val and test ...")
        proba_val  = pipe.predict_proba(X_val)[:, 1]
        proba_test = pipe.predict_proba(X_test)[:, 1]

        # ---- Val: find best F1 threshold ---------------------------------- #
        log.info(f"Scanning {N_THRESH} thresholds on val set for best F1 ...")
        best_thresh, val_best = best_f1_threshold(proba_val, y_val)
        pred_val_05   = (proba_val >= 0.5).astype("int8")
        val_t05       = _metrics(y_val, proba_val, pred_val_05)
        log.info(
            f"Val  [t=0.5]    ROC={val_t05['roc_auc']:.4f}  PR={val_t05['pr_auc']:.4f}  "
            f"F1={val_t05['f1']:.4f}  P={val_t05['precision']:.4f}  R={val_t05['recall']:.4f}"
        )
        log.info(
            f"Val  [t={best_thresh:.4f}] ROC={val_best['roc_auc']:.4f}  PR={val_best['pr_auc']:.4f}  "
            f"F1={val_best['f1']:.4f}  P={val_best['precision']:.4f}  R={val_best['recall']:.4f}"
        )

        # ---- Test metrics ------------------------------------------------- #
        pred_test_05   = (proba_test >= 0.5).astype("int8")
        pred_test_best = (proba_test >= best_thresh).astype("int8")
        test_t05  = _metrics(y_test, proba_test, pred_test_05)
        test_best = _metrics(y_test, proba_test, pred_test_best)
        log.info(
            f"Test [t=0.5]    ROC={test_t05['roc_auc']:.4f}  PR={test_t05['pr_auc']:.4f}  "
            f"F1={test_t05['f1']:.4f}  P={test_t05['precision']:.4f}  R={test_t05['recall']:.4f}"
        )
        log.info(
            f"Test [t={best_thresh:.4f}] ROC={test_best['roc_auc']:.4f}  PR={test_best['pr_auc']:.4f}  "
            f"F1={test_best['f1']:.4f}  P={test_best['precision']:.4f}  R={test_best['recall']:.4f}"
        )

        # ---- Score all HDFS sessions ------------------------------------- #
        log.info("Scoring all HDFS sessions ...")
        proba_all = pipe.predict_proba(X)[:, 1]
        pred_all_05   = (proba_all >= 0.5).astype("int8")
        pred_all_best = (proba_all >= best_thresh).astype("int8")

        scores_df = pd.DataFrame({
            "session_id":  ids_all,
            "label":       y,
            "proba":       proba_all.astype("float32"),
            "pred_0_5":    pred_all_05,
            "pred_bestF1": pred_all_best,
        })
        SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
        scores_df.to_csv(SCORES_FILE, index=False)
        log.info(f"Scores saved: {SCORES_FILE}  ({len(scores_df):,} rows)")

        # ---- Save model -------------------------------------------------- #
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as fh:
            pickle.dump(pipe, fh, protocol=pickle.HIGHEST_PROTOCOL)
        model_kb = MODEL_FILE.stat().st_size / 1024
        log.info(f"Model saved: {MODEL_FILE}  ({model_kb:.1f} KB)")

        # ---- Plots -------------------------------------------------------- #
        PLOT_DIR.mkdir(parents=True, exist_ok=True)
        log.info("Generating plots ...")
        plot_roc(y_test, proba_test, PLOT_DIR / "roc_curve_hdfs_v1.png", log)
        plot_pr( y_test, proba_test, PLOT_DIR / "pr_curve_hdfs_v1.png",  log)
        plot_confusion(y_test, pred_test_05, pred_test_best,
                       PLOT_DIR / "confusion_hdfs_v1.png", log)

        elapsed  = time.time() - start_time
        peak_mem = mem_mb()
        log.info(f"Total elapsed: {elapsed:.1f}s  |  Peak memory: {peak_mem:.1f} MB")

        # ---- Report ------------------------------------------------------ #
        write_report(sizes, anomaly_rate,
                     val_t05, val_best, best_thresh,
                     test_t05, test_best,
                     elapsed, peak_mem, log)

    except Exception:
        print(traceback.format_exc())
        sys.exit(1)

    # ---- Console summary ------------------------------------------------- #
    generated = [
        MODEL_FILE,
        SCORES_FILE,
        REPORT_FILE,
        LOG_FILE,
        PLOT_DIR / "roc_curve_hdfs_v1.png",
        PLOT_DIR / "pr_curve_hdfs_v1.png",
        PLOT_DIR / "confusion_hdfs_v1.png",
        Path(__file__),
    ]

    print()
    print("=" * 60)
    print(f"  HDFS sessions  : {n_hdfs:,}  (anomaly rate {anomaly_rate:.2%})")
    print(f"  Features       : {n_features}")
    print(f"  Train time     : {train_time:.1f}s")
    print(f"  Best F1 thresh : {best_thresh:.5f}  (from val)")
    print()
    print("  Test metrics:")
    print(f"    [t=0.5]    ROC={test_t05['roc_auc']:.4f}  PR={test_t05['pr_auc']:.4f}  "
          f"F1={test_t05['f1']:.4f}  P={test_t05['precision']:.4f}  R={test_t05['recall']:.4f}")
    print(f"    [bestF1]   ROC={test_best['roc_auc']:.4f}  PR={test_best['pr_auc']:.4f}  "
          f"F1={test_best['f1']:.4f}  P={test_best['precision']:.4f}  R={test_best['recall']:.4f}")
    print()
    print("  Generated files:")
    for f in generated:
        print(f"    {f}")
    print()
    print(f"  Elapsed : {elapsed:.1f}s   |   Peak mem: {peak_mem:.1f} MB")
    print("=" * 60)
    print()
    print("Stage 26 (HDFS supervised) completed successfully.")


if __name__ == "__main__":
    main()
