# Stage 26 V2 HDFS Supervised — Model Selection Report

**Generated:** 2026-03-03  
**Execution time:** 51.4s  
**Peak memory:** 3417.5 MB  

---

## Dataset

| Split | Rows | Anomalies | Anomaly Rate |
|-------|-----:|----------:|-------------:|
| Train | 323,343 | 7,592 | 2.35% |
| Val   | 40,418   | 949   | 2.35% |
| Test  | 40,418  | 949  | 2.35% |
| **Total HDFS** | 404,179 | 9,490 | 2.35% |

---

## Model Comparison — Validation Set (PR-AUC is selection criterion)

| Model | Val ROC AUC | Val PR AUC | Train time | Selected |
|-------|------------:|-----------:|-----------:|:--------:|
| LogReg-L2 | 0.6604 | 0.2334 | 11.6s | **YES** |
| HGBC | 0.6555 | 0.1845 | 23.3s |  |

---

## Chosen Model

**LogReg-L2**  
Parameters: `{'C': 1.0, 'class_weight': 'balanced', 'dual': False, 'fit_intercept': True, 'intercept_scaling': 1, 'l1_ratio': 0, 'max_iter': 4000, 'n_jobs': None, 'penalty': 'deprecated', 'random_state': 42, 'solver': 'lbfgs', 'tol': 0.0001, 'verbose': 0, 'warm_start': False}`  
Best F1 threshold (from val): `0.71259`

---

## Test Metrics

| Threshold | ROC AUC | PR AUC | Precision | Recall | F1 | Pred Anom% |
|-----------|--------:|-------:|----------:|-------:|---:|-----------:|
| 0.5 | 0.6624 | 0.1864 | 0.0475 | 0.4594 | 0.0862 | 22.69% |
| bestF1=0.7126 | 0.6624 | 0.1864 | 0.4261 | 0.1791 | 0.2522 | 0.99% |

---

## Confusion Matrix — Test Set (bestF1 threshold)

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 39,240 (TN) | 229 (FP) |
| **Actual Anomaly** | 779 (FN) | 170 (TP) |

---

## Generated Plots

| Plot | File |
|------|------|
| ROC Curve | `ai_workspace/stage_26_hdfs_supervised/roc_curve_hdfs_v2.png` |
| PR Curve  | `ai_workspace/stage_26_hdfs_supervised/pr_curve_hdfs_v2.png` |
| Confusion | `ai_workspace/stage_26_hdfs_supervised/confusion_hdfs_v2.png` |

---

*Stage 26 (v2) completed successfully.*
