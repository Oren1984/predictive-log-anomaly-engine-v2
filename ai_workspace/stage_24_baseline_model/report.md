# Stage 24 V2 Baseline Model Report

**Generated:** 2026-03-03  
**Execution time:** 26.9s  
**Peak memory:** 2528.5 MB  

---

## Model Configuration

| Parameter | Value |
|-----------|-------|
| Model | IsolationForest |
| n_estimators | 300 |
| random_state | 42 |
| Feature count | 404 |
| Training sessions | 495,405 |
| Training time | 0.8s |
| Observed anomaly rate | 19.08% |

---

## Score Distribution

*(score = -score_samples; higher = more anomalous)*

| Stat | Value |
|------|------:|
| Min    | 0.29739 |
| p1     | 0.29914 |
| Mean   | 0.31899 |
| Median | 0.31819 |
| p95    | 0.34959 |
| p99    | 0.36727 |
| Max    | 0.44266 |

---

## Overall Threshold (F1-optimal)

| Metric | Value |
|--------|------:|
| Threshold | 0.30665 |
| F1        | 0.3846 |
| Precision | 0.2537 |
| Recall    | 0.7948 |
| Predicted anomalies | 296,066 (59.76%) |

**Confusion matrix (pred_overall):**

| | Pred Normal | Pred Anomaly |
|---|---:|---:|
| **Actual Normal**  | 179,945 (TN) | 220,952 (FP) |
| **Actual Anomaly** | 19,394 (FN) | 75,114 (TP) |

```
              precision    recall  f1-score   support

           0       0.90      0.45      0.60    400897
           1       0.25      0.79      0.38     94508

    accuracy                           0.51    495405
   macro avg       0.58      0.62      0.49    495405
weighted avg       0.78      0.51      0.56    495405

```

---

## Per-Dataset Thresholds (F1-optimal per dataset)

| Dataset | N | Anomalies | Threshold | F1 | Precision | Recall | Pred Anom % |
|---------|--:|----------:|----------:|---:|----------:|-------:|------------:|
| bgl | 91,226 | 85,018 (93.19%) | 0.29739 | 0.9648 | 0.9319 | 1.0000 | 100.00% |
| hdfs | 404,179 | 9,490 (2.35%) | 0.30664 | 0.0466 | 0.0243 | 0.5686 | 54.95% |

---

## Output Files

| File | Description |
|------|-------------|
| `isolation_forest_v2.pkl` | Trained IsolationForest (n_estimators=300) |
| `session_scores_v2.csv` | 495,405 rows: session_id, dataset, label, score, pred_overall, pred_by_dataset |

---

*Stage 24 (v2) completed successfully.*
