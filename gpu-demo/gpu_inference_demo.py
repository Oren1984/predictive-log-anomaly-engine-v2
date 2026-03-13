# ==============================================================================
# gpu_inference_demo.py
#
# Predictive Log Anomaly Engine — GPU Inference Demo
#
# PURPOSE:
#   Standalone script that demonstrates how the project's real inference
#   components run on GPU (with automatic CPU fallback).
#
#   This script uses the actual production classes from src/:
#     - NextTokenTransformerModel  (GPT-style causal transformer)
#     - AnomalyScorer              (NLL-based sequence scorer)
#     - BaselineAnomalyModel       (IsolationForest wrapper)
#     - BaselineFeatureExtractor   (token-frequency feature builder)
#     - AlertPolicy                (severity classifier)
#     - Sequence                   (core sequence domain model)
#
# USAGE:
#   python gpu_inference_demo.py
#
# REQUIREMENTS:
#   Run from the project root. Artifacts must exist at:
#     models/transformer.pt
#     models/baseline.pkl
#     artifacts/threshold.json
#     artifacts/threshold_transformer.json
#
#   If artifacts are missing the script degrades gracefully to an
#   untrained-model demonstration and prints a clear notice.
#
# NO DOCKER REQUIRED. NO NEW DEPENDENCIES.
# ==============================================================================

import sys
import time
import json
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so src/ imports resolve correctly
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Suppress noisy sub-loggers during demo
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

import torch
import numpy as np

# ==============================================================================
# SECTION 1 — BANNER
# ==============================================================================

DIVIDER = "-" * 56

def banner():
    print(DIVIDER)
    print("  Predictive Log Anomaly Engine")
    print("  GPU Inference Demo")
    print(DIVIDER)

banner()

# ==============================================================================
# SECTION 2 — DEVICE DETECTION
# ==============================================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
device_label = "CUDA (GPU)" if device.type == "cuda" else "CPU (no GPU detected)"
print(f"\nDevice detected: {device_label}")

if device.type == "cuda":
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb  = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU name : {gpu_name}")
    print(f"  VRAM     : {vram_gb:.1f} GB")

# ==============================================================================
# SECTION 3 — IMPORT PROJECT COMPONENTS
# ==============================================================================

from src.modeling.transformer.model  import NextTokenTransformerModel
from src.modeling.transformer.config import TransformerConfig
from src.modeling.transformer.scorer import AnomalyScorer
from src.modeling.baseline.model     import BaselineAnomalyModel
from src.modeling.baseline.extractor import BaselineFeatureExtractor
from src.alerts.models               import AlertPolicy
from src.sequencing.models           import Sequence

ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
MODEL_DIR    = PROJECT_ROOT / "models"

# ==============================================================================
# SECTION 4 — LOAD TRANSFORMER MODEL ONTO DETECTED DEVICE
# ==============================================================================

print("\nLoading transformer model...")

TRANSFORMER_PATH = MODEL_DIR / "transformer.pt"
THRESHOLD_T_PATH = ARTIFACT_DIR / "threshold_transformer.json"

_transformer_loaded = False
_threshold_transformer = 0.034   # project default

if TRANSFORMER_PATH.exists():
    try:
        # Load weights, then move the full model to the target device
        transformer_model = NextTokenTransformerModel.load(
            str(TRANSFORMER_PATH), map_location=str(device)
        )
        transformer_model.to(device)
        transformer_model.eval()

        if THRESHOLD_T_PATH.exists():
            _threshold_transformer = json.loads(
                THRESHOLD_T_PATH.read_text()
            )["threshold"]

        cfg = transformer_model.cfg
        scorer = AnomalyScorer(
            model=transformer_model,
            cfg=cfg,
            device=str(device),
        )
        scorer.set_threshold(_threshold_transformer)
        _transformer_loaded = True

        print(f"  Transformer loaded successfully on {device_label}")
        print(f"  Vocab size : {cfg.vocab_size}")
        print(f"  d_model    : {cfg.d_model}  |  heads: {cfg.n_heads}  |  layers: {cfg.n_layers}")
        print(f"  NLL threshold : {_threshold_transformer:.4f}")

    except Exception as exc:
        print(f"  [WARN] Could not load transformer.pt: {exc}")
        print("  Falling back to untrained model (shape/device demo only).")

if not _transformer_loaded:
    # Graceful fallback: build a fresh model to demonstrate the GPU path
    cfg = TransformerConfig()
    transformer_model = NextTokenTransformerModel(cfg).to(device)
    transformer_model.eval()
    scorer = AnomalyScorer(model=transformer_model, cfg=cfg, device=str(device))
    scorer.set_threshold(_threshold_transformer)
    print("  Untrained transformer initialised (device demo only).")

# ==============================================================================
# SECTION 5 — LOAD BASELINE MODEL (IsolationForest — CPU only, sklearn)
# ==============================================================================

print("\nLoading baseline model (IsolationForest)...")

BASELINE_PATH   = MODEL_DIR / "baseline.pkl"
THRESHOLD_B_PATH = ARTIFACT_DIR / "threshold.json"

_baseline_loaded = False
_threshold_baseline = 0.33

if BASELINE_PATH.exists():
    try:
        baseline_model = BaselineAnomalyModel.load(str(BASELINE_PATH))

        if THRESHOLD_B_PATH.exists():
            _threshold_baseline = json.loads(
                THRESHOLD_B_PATH.read_text()
            )["threshold"]

        _baseline_loaded = True
        print(f"  Baseline loaded successfully (IsolationForest, runs on CPU)")
        print(f"  Anomaly score threshold : {_threshold_baseline:.4f}")

    except Exception as exc:
        print(f"  [WARN] Could not load baseline.pkl: {exc}")

if not _baseline_loaded:
    print("  Baseline model not available — baseline scoring skipped.")

# ==============================================================================
# SECTION 6 — SAMPLE SEQUENCE CONSTRUCTION
# ==============================================================================
# Token IDs map to log template IDs (PAD=0, UNK=1, template N -> token N+2).
# Normal HDFS sessions use a small set of repeated templates (low entropy).
# Anomalous sequences mix in rare/unexpected template IDs (high entropy).

print("\n" + DIVIDER)
print("  Constructing sample log windows...")
print(DIVIDER)

SAMPLE_SEQUENCES = [
    Sequence(
        sequence_id="hdfs-normal-01",
        tokens=[2, 3, 4, 2, 3, 4, 2, 3, 5, 4],     # tight, repetitive pattern
        timestamps=[1.0 * i for i in range(10)],
        label=0,
    ),
    Sequence(
        sequence_id="hdfs-normal-02",
        tokens=[2, 2, 3, 4, 3, 4, 5, 2, 3, 4],
        timestamps=[1.0 * i for i in range(10)],
        label=0,
    ),
    Sequence(
        sequence_id="bgl-anomaly-01",
        tokens=[2, 3, 412, 87, 1203, 9, 3, 4, 512, 2041],  # rare IDs injected
        timestamps=[1.0 * i for i in range(10)],
        label=1,
    ),
    Sequence(
        sequence_id="bgl-anomaly-02",
        tokens=[5, 6, 7, 1400, 1401, 1402, 8, 9, 6500, 7100],  # highly unusual
        timestamps=[1.0 * i for i in range(10)],
        label=1,
    ),
    Sequence(
        sequence_id="hdfs-borderline-01",
        tokens=[2, 3, 4, 5, 102, 3, 4, 2, 88, 4],    # mostly normal, one outlier
        timestamps=[1.0 * i for i in range(10)],
        label=0,
    ),
]

print(f"  {len(SAMPLE_SEQUENCES)} sequences prepared "
      f"(10 tokens each, window_size=10)")
for seq in SAMPLE_SEQUENCES:
    tag = "ANOMALY" if seq.label == 1 else "NORMAL "
    print(f"    [{tag}] {seq.sequence_id}")

# ==============================================================================
# SECTION 7 — TRANSFORMER INFERENCE ON DETECTED DEVICE
# ==============================================================================

print("\n" + DIVIDER)
print(f"  Running Transformer (NLL) Inference on {device_label}")
print(DIVIDER)

policy = AlertPolicy(cooldown_seconds=0.0)   # no cooldown for demo

t0 = time.perf_counter()
transformer_scores = scorer.score(SAMPLE_SEQUENCES)
elapsed_ms = (time.perf_counter() - t0) * 1000

print(f"\n  Scored {len(SAMPLE_SEQUENCES)} sequences in {elapsed_ms:.1f} ms")
if _transformer_loaded:
    print("  Note: demo token IDs are synthetic and do not match the training")
    print("  distribution, so NLL scores will be high for all sequences.")
    print("  This is expected. The demo focuses on the device/pipeline path,")
    print("  not prediction accuracy on out-of-distribution inputs.")
print()

results = []

for seq, score in zip(SAMPLE_SEQUENCES, transformer_scores):
    is_anomaly    = float(score) >= _threshold_transformer
    severity      = policy.classify_severity(float(score), _threshold_transformer)
    true_label    = "ANOMALY" if seq.label == 1 else "NORMAL "
    detected      = "ANOMALY" if is_anomaly       else "NORMAL "

    results.append({
        "sequence_id": seq.sequence_id,
        "true_label":  true_label,
        "score":       float(score),
        "threshold":   _threshold_transformer,
        "is_anomaly":  is_anomaly,
        "severity":    severity.upper() if is_anomaly else "none",
        "correct":     true_label.strip() == detected.strip(),
    })

    match_icon = "OK" if true_label.strip() == detected.strip() else "!!"
    print(f"  [{match_icon}] {seq.sequence_id:<28} "
          f"score={score:.4f}  threshold={_threshold_transformer:.4f}  "
          f"detected={detected}  severity={severity.upper() if is_anomaly else 'none':<8}")

# ==============================================================================
# SECTION 8 — BASELINE INFERENCE (CPU — IsolationForest)
# ==============================================================================

if _baseline_loaded:
    print("\n" + DIVIDER)
    print("  Running Baseline (IsolationForest) Inference on CPU")
    print(DIVIDER + "\n")

    # The pretrained baseline.pkl was fitted with BaselineFeatureExtractor(top_k=100)
    # on the full training split (sequences_train.parquet), producing 204 features.
    # To use the pretrained model the extractor must be re-fit on the same training
    # split so the feature columns align.  We attempt to load that split here.
    _baseline_scored = False
    train_parquet = PROJECT_ROOT / "data" / "processed" / "sequences_train.parquet"

    if train_parquet.exists():
        try:
            import pandas as pd
            import json as _json

            df_train = pd.read_parquet(train_parquet)
            train_seqs = []
            for _, row in df_train.iterrows():
                raw = row.get("tokens", "[]")
                tokens = _json.loads(raw) if isinstance(raw, str) else list(raw)
                train_seqs.append(Sequence(
                    sequence_id=str(row.get("sequence_id", "")),
                    tokens=[int(t) for t in tokens],
                    label=int(row.get("label", 0)) if row.get("label") is not None else None,
                ))

            extractor = BaselineFeatureExtractor(top_k=100)
            extractor.fit(train_seqs)
            X = extractor.transform(SAMPLE_SEQUENCES)

            t0 = time.perf_counter()
            baseline_scores = baseline_model.score(X)
            elapsed_ms_b = (time.perf_counter() - t0) * 1000
            _baseline_scored = True
            print(f"  Extractor re-fitted on {len(train_seqs)} training sequences "
                  f"({extractor.n_features} features)")
            print(f"  Scored {len(SAMPLE_SEQUENCES)} sequences in {elapsed_ms_b:.1f} ms\n")

            for seq, b_score in zip(SAMPLE_SEQUENCES, baseline_scores):
                is_anom_b  = float(b_score) >= _threshold_baseline
                severity_b = policy.classify_severity(float(b_score), _threshold_baseline)
                true_label = "ANOMALY" if seq.label == 1 else "NORMAL "
                detected_b = "ANOMALY" if is_anom_b       else "NORMAL "
                match_icon = "OK" if true_label.strip() == detected_b.strip() else "!!"
                print(f"  [{match_icon}] {seq.sequence_id:<28} "
                      f"score={b_score:.4f}  threshold={_threshold_baseline:.4f}  "
                      f"detected={detected_b}  severity={severity_b.upper() if is_anom_b else 'none':<8}")

        except Exception as exc:
            print(f"  [WARN] Baseline scoring failed: {exc}")

    if not _baseline_scored:
        print("  [NOTE] Baseline scoring skipped.")
        print("  The pretrained IsolationForest requires 204 features produced by")
        print("  BaselineFeatureExtractor(top_k=100) fit on sequences_train.parquet.")
        print("  That file is not present in this environment.")
        print("  The full pipeline (InferenceEngine) handles this automatically.")
        print("  Run: python -m uvicorn src.api.app:create_app --factory --port 8000")

# ==============================================================================
# SECTION 9 — ENSEMBLE SUMMARY (when both models available)
# ==============================================================================

if _baseline_loaded and _transformer_loaded and _baseline_scored:
    print("\n" + DIVIDER)
    print("  Ensemble Summary (Transformer + Baseline, normalised)")
    print(DIVIDER + "\n")

    # Reuse the extractor already fitted on training sequences in Section 8
    X_ens = extractor.transform(SAMPLE_SEQUENCES)
    b_scores_ens = baseline_model.score(X_ens)
    t_scores_ens = transformer_scores

    # Same normalisation used in src/runtime/inference_engine.py
    thr_b = max(_threshold_baseline,    1e-9)
    thr_t = max(_threshold_transformer, 1e-9)
    _threshold_ensemble = 1.0   # normalised; 1.0 = either model votes anomalous

    for seq, b_s, t_s in zip(SAMPLE_SEQUENCES, b_scores_ens, t_scores_ens):
        b_norm  = float(b_s) / thr_b
        t_norm  = float(t_s) / thr_t
        ens     = (b_norm + t_norm) / 2.0
        is_anom = ens >= _threshold_ensemble
        severity = policy.classify_severity(ens, _threshold_ensemble)
        true_label = "ANOMALY" if seq.label == 1 else "NORMAL "
        detected   = "ANOMALY" if is_anom       else "NORMAL "
        match_icon = "OK" if true_label.strip() == detected.strip() else "!!"
        print(f"  [{match_icon}] {seq.sequence_id:<28} "
              f"ens={ens:.4f}  detected={detected}  "
              f"severity={severity.upper() if is_anom else 'none':<8}")

# ==============================================================================
# SECTION 10 — FINAL SUMMARY
# ==============================================================================

print("\n" + DIVIDER)
print("  Demo Complete")
print(DIVIDER)
print(f"  Device used          : {device_label}")
print(f"  Transformer loaded   : {'Yes (pretrained)' if _transformer_loaded else 'No (untrained fallback)'}")
print(f"  Baseline loaded      : {'Yes (pretrained)' if _baseline_loaded   else 'No'}")
print(f"  Sequences scored     : {len(SAMPLE_SEQUENCES)}")
anomaly_count = sum(1 for r in results if r["is_anomaly"])
print(f"  Anomalies detected   : {anomaly_count}/{len(SAMPLE_SEQUENCES)} "
      f"(transformer NLL, threshold={_threshold_transformer:.4f})")
print(DIVIDER)
print()
print("  This demo uses the real inference classes from src/.")
print("  For the full pipeline with REST API, run:")
print("    python -m uvicorn src.api.app:create_app --factory --port 8000")
print(DIVIDER)
