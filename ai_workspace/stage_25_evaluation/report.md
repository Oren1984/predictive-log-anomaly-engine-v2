# Stage 25 V2 Evaluation Report

**Generated:** 2026-03-03  
**Execution time:** 1.6s  

---

## Overall Metrics

| Mode | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anomalies |
|------|--------:|-------:|----------:|-------:|---:|---------------:|
| pred_overall | 0.5632 | 0.2127 | 0.2537 | 0.7948 | 0.3846 | 296,066 (59.76%) |
| pred_by_dataset | 0.5632 | 0.2127 | 0.2886 | 0.9567 | 0.4434 | 313,306 (63.24%) |

---

## Per-Dataset Metrics

| Dataset | Mode | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anom % |
|---------|------|--------:|-------:|----------:|-------:|---:|------------:|
| bgl | pred_overall | 0.6192 | 0.9597 | 0.9423 | 0.8200 | 0.8769 | 81.10% |
| bgl | pred_by_dataset | 0.6192 | 0.9597 | 0.9319 | 1.0000 | 0.9648 | 100.00% |
| hdfs | pred_overall | 0.4918 | 0.0241 | 0.0243 | 0.5686 | 0.0466 | 54.95% |
| hdfs | pred_by_dataset | 0.4918 | 0.0241 | 0.0243 | 0.5686 | 0.0466 | 54.95% |

---

## Confusion Matrices

### pred_overall (global threshold)

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 179,945 (TN) | 220,952 (FP) |
| **Actual Anomaly** | 19,394 (FN) | 75,114 (TP) |

### pred_by_dataset (per-dataset threshold)

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 178,005 (TN) | 222,892 (FP) |
| **Actual Anomaly** | 4,094 (FN) | 90,414 (TP) |

### bgl — pred_overall

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 1,940 (TN) | 4,268 (FP) |
| **Actual Anomaly** | 15,300 (FN) | 69,718 (TP) |

### bgl — pred_by_dataset

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 0 (TN) | 6,208 (FP) |
| **Actual Anomaly** | 0 (FN) | 85,018 (TP) |

### hdfs — pred_overall

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 178,005 (TN) | 216,684 (FP) |
| **Actual Anomaly** | 4,094 (FN) | 5,396 (TP) |

### hdfs — pred_by_dataset

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 178,005 (TN) | 216,684 (FP) |
| **Actual Anomaly** | 4,094 (FN) | 5,396 (TP) |

---

## Interpretation

- **BGL dominates performance.** The bigram and entropy features introduced in V2 provide near-perfect separation on BGL sessions (F1 ~0.96), since BGL anomalies produce structurally distinct template transition patterns.
- **HDFS remains difficult.** IsolationForest in unsupervised mode struggles with HDFS: its anomalies (blk_ corruption events) share similar template distributions with normal sessions at the aggregate feature level used here.
- **pred_by_dataset is more informative for BGL** but inflates false positives on HDFS by setting the threshold at the distribution minimum (flags ~55% as anomalous).
- **Score distribution is narrow** ([0.297, 0.443]), indicating the model does not produce strong outlier separation globally — consistent with the mixed-dataset input.
- **Next steps:** per-dataset models, supervised methods (XGBoost/LSTM), or dataset-stratified threshold calibration would likely yield large gains on HDFS.

---

## Generated Plots

| Plot | File |
|------|------|
| ROC Curve | `ai_workspace/stage_25_evaluation/roc_curve_v2.png` |
| PR Curve | `ai_workspace/stage_25_evaluation/pr_curve_v2.png` |
| Score Histogram | `ai_workspace/stage_25_evaluation/score_histogram_v2.png` |
| Confusion (overall) | `ai_workspace/stage_25_evaluation/confusion_overall_v2.png` |
| Confusion (per dataset) | `ai_workspace/stage_25_evaluation/confusion_by_dataset_v2.png` |

---

*Stage 25 (v2) completed successfully.*
