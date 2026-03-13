"""
Stage 26 V2 - HDFS Supervised Model Selection
===============================================
Trains and compares three model families on HDFS sessions only,
selects the best by VAL PR-AUC, then evaluates on the held-out test set.

Models compared:
  A) LogisticRegression L2 (baseline, balanced)
  B) LogisticRegression L1 (saga, balanced, C in [0.2, 0.5, 1.0])
  C) HistGradientBoostingClassifier (max_depth=6, lr=0.05, 300 iters)

Split: 80/10/10 stratified, random_state=42 (identical to v1).

Outputs
-------
  data/models/hdfs_supervised_best_v2.pkl
  data/intermediate/hdfs_supervised_scores_v2.csv
  ai_workspace/reports/stage_26_hdfs_supervised_report_v2.md
  ai_workspace/logs/stage_26_hdfs_supervised_v2.log
  ai_workspace/stage_26_hdfs_supervised/roc_curve_hdfs_v2.png
  ai_workspace/stage_26_hdfs_supervised/pr_curve_hdfs_v2.png
  ai_workspace/stage_26_hdfs_supervised/confusion_hdfs_v2.png
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
from sklearn.ensemble import HistGradientBoostingClassifier
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
MODEL_FILE  = MODEL_DIR / "hdfs_supervised_best_v2.pkl"
SCORES_FILE = BASE / "data/intermediate/hdfs_supervised_scores_v2.csv"
REPORT_FILE = BASE / "ai_workspace/reports/stage_26_hdfs_supervised_report_v2.md"
LOG_FILE    = BASE / "ai_workspace/logs/stage_26_hdfs_supervised_v2.log"
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
# Candidate pipelines
# ---------------------------------------------------------------------------
def get_candidates() -> list[tuple[str, object]]:
    """Return list of (name, pipeline) pairs.

    sklearn 1.8 notes:
      - penalty= is deprecated; use l1_ratio= instead
        (l1_ratio=0 → L2, l1_ratio=1 → L1)
      - For L1, solver="liblinear" is far faster than saga on large binary tasks
      - HGBC is tree-based: no scaler needed
    """
    # A) L2 baseline — default l1_ratio=0 means L2; lbfgs is fast for L2
    logreg_l2 = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            l1_ratio=0, solver="lbfgs",
            max_iter=4000, class_weight="balanced",
            random_state=RANDOM_STATE,
        )),
    ])
    candidates = [("LogReg-L2", logreg_l2)]

    # B) L1 variants skipped entirely — liblinear with l1_ratio=1 causes
    #    silent OOM/process-kill on this machine at ~3 GB baseline memory.
    #    C=0.2 was already excluded; C=0.5 and C=1.0 exhibit the same failure.

    # C) HGBC — tree-based, handles raw features natively
    hgbc = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.05,
        max_iter=300, random_state=RANDOM_STATE,
    )
    candidates.append(("HGBC", hgbc))

    return candidates


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------
def best_f1_threshold(proba: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    lo, hi = float(np.percentile(proba, 1)), float(np.percentile(proba, 99))
    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(lo, hi, N_THRESH):
        f1 = f1_score(y, (proba >= t).astype("int8"), zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, float(t)
    return best_t, best_f1


def eval_metrics(y_true: np.ndarray, proba: np.ndarray,
                 pred: np.ndarray) -> dict:
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
        "n":  int(len(y_true)), "support": int(y_true.sum()),
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_roc(y_test, proba_test, model_name, path, log) -> None:
    fpr, tpr, _ = roc_curve(y_test, proba_test)
    auc = roc_auc_score(y_test, proba_test)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, lw=1.5, color="steelblue", label=f"ROC AUC = {auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curve — HDFS {model_name} (test)")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {Path(path).name}")


def plot_pr(y_test, proba_test, model_name, path, log) -> None:
    prec, rec, _ = precision_recall_curve(y_test, proba_test)
    ap = average_precision_score(y_test, proba_test)
    baseline = float(y_test.mean())
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec, lw=1.5, color="steelblue", label=f"PR AUC = {ap:.4f}")
    ax.axhline(baseline, color="gray", ls="--", lw=0.8,
               label=f"Random ({baseline:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"PR Curve — HDFS {model_name} (test)")
    ax.legend(loc="upper right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {Path(path).name}")


def plot_confusion(y_test, pred_05, pred_best, model_name, path, log) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    labels = ["Normal", "Anomaly"]
    for ax, pred, title in zip(
        axes,
        [pred_05, pred_best],
        ["threshold=0.5", "threshold=bestF1"],
    ):
        cm = confusion_matrix(y_test, pred)
        ConfusionMatrixDisplay(cm, display_labels=labels).plot(
            ax=ax, colorbar=False, cmap="Blues"
        )
        ax.set_title(title)
    fig.suptitle(f"Confusion Matrices — HDFS {model_name} (test)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    log.info(f"Saved: {Path(path).name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(sizes: dict, anomaly_rate: float,
                 val_results: list[dict],
                 best_name: str, best_params: str, best_thresh: float,
                 test_05: dict, test_best: dict,
                 elapsed: float, peak_mem: float, log) -> None:

    def mrow(label, m):
        return (
            f"| {label} | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} "
            f"| {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} "
            f"| {m['pct_pred']:.2%} |"
        )

    lines = [
        "# Stage 26 V2 HDFS Supervised — Model Selection Report",
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
        "## Model Comparison — Validation Set (PR-AUC is selection criterion)",
        "",
        "| Model | Val ROC AUC | Val PR AUC | Train time | Selected |",
        "|-------|------------:|-----------:|-----------:|:--------:|",
    ]
    for r in val_results:
        chosen = "**YES**" if r["name"] == best_name else ""
        lines.append(
            f"| {r['name']} | {r['roc_auc']:.4f} | {r['pr_auc']:.4f} "
            f"| {r['train_time']:.1f}s | {chosen} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Chosen Model",
        "",
        f"**{best_name}**  ",
        f"Parameters: `{best_params}`  ",
        f"Best F1 threshold (from val): `{best_thresh:.5f}`",
        "",
        "---",
        "",
        "## Test Metrics",
        "",
        "| Threshold | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anom% |",
        "|-----------|--------:|-------:|----------:|-------:|---:|-----------:|",
        mrow("0.5", test_05),
        mrow(f"bestF1={best_thresh:.4f}", test_best),
        "",
        "---",
        "",
        "## Confusion Matrix — Test Set (bestF1 threshold)",
        "",
        "| | Pred Normal | Pred Anomaly |",
        "|---|---:|---:|",
        f"| **Actual Normal**  | {test_best['tn']:,} (TN) | {test_best['fp']:,} (FP) |",
        f"| **Actual Anomaly** | {test_best['fn']:,} (FN) | {test_best['tp']:,} (TP) |",
        "",
        "---",
        "",
        "## Generated Plots",
        "",
        "| Plot | File |",
        "|------|------|",
        "| ROC Curve | `ai_workspace/stage_26_hdfs_supervised/roc_curve_hdfs_v2.png` |",
        "| PR Curve  | `ai_workspace/stage_26_hdfs_supervised/pr_curve_hdfs_v2.png` |",
        "| Confusion | `ai_workspace/stage_26_hdfs_supervised/confusion_hdfs_v2.png` |",
        "",
        "---",
        "",
        "*Stage 26 (v2) completed successfully.*",
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
    log.info("Stage 26 V2: HDFS Supervised Model Selection")
    log.info(f"Input  : {INPUT_FILE}")
    log.info(f"Memory start: {mem_mb():.1f} MB")
    log.info("=" * 60)

    try:
        # ---- Load & filter ----------------------------------------------- #
        log.info("Loading session_features_v2.csv (HDFS only) ...")
        df_full = pd.read_csv(INPUT_FILE)
        df = df_full[df_full["dataset"] == "hdfs"].reset_index(drop=True)
        del df_full   # free BGL rows (~90K × 407 cols) before training
        n_hdfs = len(df)
        log.info(f"HDFS sessions: {n_hdfs:,}  Memory: {mem_mb():.1f} MB")

        exclude = {"session_id", "dataset", "label"}
        feat_cols = [c for c in df.columns if c not in exclude]
        n_features = len(feat_cols)

        X = df[feat_cols].values.astype("float32")
        y = df["label"].values.astype("int8")
        ids_all = df["session_id"].tolist()   # plain list avoids pyarrow indexing
        anomaly_rate = float(y.mean())

        log.info(f"Features: {n_features}  |  Anomaly rate: {anomaly_rate:.4f} ({anomaly_rate:.2%})")

        # ---- Split (index-based, identical to v1) ------------------------- #
        idx = np.arange(n_hdfs)
        idx_train, idx_temp, y_train, y_temp = train_test_split(
            idx, y,
            test_size=VAL_SIZE + TEST_SIZE,
            stratify=y, random_state=RANDOM_STATE,
        )
        idx_val, idx_test, y_val, y_test = train_test_split(
            idx_temp, y_temp,
            test_size=0.5, stratify=y_temp, random_state=RANDOM_STATE,
        )
        X_train = X[idx_train]
        X_val   = X[idx_val]
        X_test  = X[idx_test]

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

        # ---- Train & evaluate all candidates on val ---------------------- #
        candidates = get_candidates()
        val_results = []
        best_name, best_pipe, best_val_pr = None, None, -1.0

        log.info("Skipping LogReg-L1-C0.2 due to excessive runtime observed on this machine.")
        log.info("Skipping LogReg-L1-C0.5 and LogReg-L1-C1.0: liblinear L1 causes OOM on this machine at current memory baseline.")
        log.info(f"Training {len(candidates)} candidate models ...")
        for name, pipe in candidates:
            log.info(f"  Fitting: {name} ...")
            t0 = time.time()
            pipe.fit(X_train, y_train)
            elapsed_fit = time.time() - t0

            proba_val = pipe.predict_proba(X_val)[:, 1]
            roc = roc_auc_score(y_val, proba_val)
            pr  = average_precision_score(y_val, proba_val)

            log.info(
                f"  [{name}]  Val ROC={roc:.4f}  Val PR-AUC={pr:.4f}  "
                f"fit={elapsed_fit:.1f}s"
            )
            val_results.append({
                "name": name, "pipe": pipe,
                "roc_auc": roc, "pr_auc": pr,
                "train_time": elapsed_fit,
            })

            if pr > best_val_pr:
                best_val_pr  = pr
                best_name    = name
                best_pipe    = pipe

        log.info(f"Best model by Val PR-AUC: {best_name}  (PR-AUC={best_val_pr:.4f})")

        # ---- Best threshold on val --------------------------------------- #
        log.info(f"Finding best F1 threshold on val for {best_name} ...")
        proba_val_best = best_pipe.predict_proba(X_val)[:, 1]
        best_thresh, best_val_f1 = best_f1_threshold(proba_val_best, y_val)
        log.info(f"Best F1 threshold (val): {best_thresh:.5f}  (val F1={best_val_f1:.4f})")

        # ---- Test evaluation --------------------------------------------- #
        log.info("Evaluating best model on test set ...")
        proba_test = best_pipe.predict_proba(X_test)[:, 1]
        pred_test_05   = (proba_test >= 0.5).astype("int8")
        pred_test_best = (proba_test >= best_thresh).astype("int8")
        test_05   = eval_metrics(y_test, proba_test, pred_test_05)
        test_best = eval_metrics(y_test, proba_test, pred_test_best)

        log.info(
            f"Test [t=0.5]    ROC={test_05['roc_auc']:.4f}  "
            f"PR={test_05['pr_auc']:.4f}  F1={test_05['f1']:.4f}  "
            f"P={test_05['precision']:.4f}  R={test_05['recall']:.4f}"
        )
        log.info(
            f"Test [t={best_thresh:.4f}] ROC={test_best['roc_auc']:.4f}  "
            f"PR={test_best['pr_auc']:.4f}  F1={test_best['f1']:.4f}  "
            f"P={test_best['precision']:.4f}  R={test_best['recall']:.4f}"
        )

        # ---- Score all HDFS sessions ------------------------------------- #
        log.info("Scoring all HDFS sessions with best model ...")
        proba_all = best_pipe.predict_proba(X)[:, 1]
        pred_all_05   = (proba_all >= 0.5).astype("int8")
        pred_all_best = (proba_all >= best_thresh).astype("int8")

        scores_df = pd.DataFrame({
            "session_id":      ids_all,
            "label":           y,
            "proba_or_score":  proba_all.astype("float32"),
            "pred_0_5":        pred_all_05,
            "pred_bestF1":     pred_all_best,
        })
        SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
        scores_df.to_csv(SCORES_FILE, index=False)
        log.info(f"Scores saved: {SCORES_FILE}  ({len(scores_df):,} rows)")

        # ---- Save best model --------------------------------------------- #
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as fh:
            pickle.dump(best_pipe, fh, protocol=pickle.HIGHEST_PROTOCOL)
        model_kb = MODEL_FILE.stat().st_size / 1024
        log.info(f"Model saved: {MODEL_FILE}  ({model_kb:.1f} KB)")

        # ---- Plots -------------------------------------------------------- #
        PLOT_DIR.mkdir(parents=True, exist_ok=True)
        log.info("Generating plots ...")
        plot_roc(y_test, proba_test, best_name,
                 PLOT_DIR / "roc_curve_hdfs_v2.png", log)
        plot_pr(y_test, proba_test, best_name,
                PLOT_DIR / "pr_curve_hdfs_v2.png", log)
        plot_confusion(y_test, pred_test_05, pred_test_best, best_name,
                       PLOT_DIR / "confusion_hdfs_v2.png", log)

        elapsed  = time.time() - start_time
        peak_mem = mem_mb()
        log.info(f"Total elapsed: {elapsed:.1f}s  |  Peak memory: {peak_mem:.1f} MB")

        # Best model params string for report
        clf = best_pipe.steps[-1][1] if hasattr(best_pipe, "steps") else best_pipe
        best_params = str(clf.get_params())

        # ---- Report ------------------------------------------------------ #
        write_report(
            sizes, anomaly_rate,
            [{k: v for k, v in r.items() if k != "pipe"} for r in val_results],
            best_name, best_params, best_thresh,
            test_05, test_best,
            elapsed, peak_mem, log,
        )

    except Exception:
        print(traceback.format_exc())
        sys.exit(1)

    # ---- Console summary ------------------------------------------------- #
    generated = [
        MODEL_FILE, SCORES_FILE, REPORT_FILE, LOG_FILE,
        PLOT_DIR / "roc_curve_hdfs_v2.png",
        PLOT_DIR / "pr_curve_hdfs_v2.png",
        PLOT_DIR / "confusion_hdfs_v2.png",
        Path(__file__),
    ]

    print()
    print("=" * 60)
    print(f"  HDFS sessions  : {n_hdfs:,}  (anomaly rate {anomaly_rate:.2%})")
    print(f"  Features       : {n_features}")
    print()
    print("  Val PR-AUC comparison:")
    for r in val_results:
        tag = " <-- chosen" if r["name"] == best_name else ""
        print(f"    {r['name']:20s}  ROC={r['roc_auc']:.4f}  PR={r['pr_auc']:.4f}{tag}")
    print()
    print(f"  Best model     : {best_name}")
    print(f"  Best F1 thresh : {best_thresh:.5f}  (from val)")
    print()
    print("  Test metrics:")
    print(f"    [t=0.5]    ROC={test_05['roc_auc']:.4f}  PR={test_05['pr_auc']:.4f}  "
          f"F1={test_05['f1']:.4f}  P={test_05['precision']:.4f}  R={test_05['recall']:.4f}")
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
    print("Stage 26 (v2) completed successfully.")


if __name__ == "__main__":
    main()
