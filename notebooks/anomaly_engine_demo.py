# notebooks/anomaly_engine_demo.py

# Purpose: Demonstrate the end-to-end functionality of the Predictive Log Anomaly Engine.

# Input: This script processes a small set of synthetic log data, performs template mining,
# builds sliding windows of events, extracts features, scores the windows for anomalies,    
# and applies an alert policy to determine when to fire alerts.
# It also generates visualizations of the template frequency distribution and the risk scores across windows.

# Output: The script prints the intermediate dataframes and results to the console,
# saves two plots (template frequency distribution and risk score plot) to the notebooks directory,
# and demonstrates the end-to-end trace of how a single window is processed from raw logs to an alert decision.

# Used by: This script is a standalone demonstration and is not directly used by other modules.
# However, it serves as an educational example of how the components of the anomaly engine work together 
# and can be referenced in documentation or used as a basis for further development and testing.


"""
Predictive Log Anomaly Engine - End-to-End Demo Script
=======================================================
Equivalent Python script for notebooks/anomaly_engine_demo.ipynb.
Run with:  python notebooks/anomaly_engine_demo.py
Requires:  numpy, pandas, matplotlib  (sklearn optional)
Runtime:   < 5 seconds on any normal laptop.
"""

import re
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

warnings.filterwarnings("ignore")

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

print(f"sklearn available: {SKLEARN_AVAILABLE}")

# ── 1. Demo Logs ──────────────────────────────────────────────────────────────

RAW_LOGS = [
    ("2026-03-04 10:00:01", "web", "GET /api/health HTTP/1.1 200",            0),
    ("2026-03-04 10:00:02", "web", "GET /api/users HTTP/1.1 200",             0),
    ("2026-03-04 10:00:03", "db",  "Connection established from 10.0.0.5",    0),
    ("2026-03-04 10:00:04", "db",  "Query executed in 12ms SELECT users",     0),
    ("2026-03-04 10:00:05", "web", "GET /api/health HTTP/1.1 200",            0),
    ("2026-03-04 10:00:06", "db",  "ERROR: connection timeout after 30000ms", 1),
    ("2026-03-04 10:00:07", "db",  "FATAL: max connections exceeded 500/500", 1),
    ("2026-03-04 10:00:08", "web", "POST /api/login HTTP/1.1 401 FAILED",     1),
    ("2026-03-04 10:00:09", "web", "POST /api/login HTTP/1.1 401 FAILED",     1),
    ("2026-03-04 10:00:10", "db",  "Query executed in 14ms SELECT orders",    0),
]

df_logs = pd.DataFrame(RAW_LOGS, columns=["timestamp", "service", "message", "label"])
df_logs["label_text"] = df_logs["label"].map({0: "normal", 1: "ANOMALY"})
print("\n=== Demo Logs ===")
pd.set_option("display.max_colwidth", 55)
print(df_logs[["timestamp", "service", "message", "label_text"]].to_string(index=False))


# ── 2. Tokenization ───────────────────────────────────────────────────────────

def mine_template(msg: str) -> str:
    """Simplified 5-step regex template miner."""
    msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP>",     msg)
    msg = re.sub(r"\b\d+ms\b",                                 "<DUR>",   msg)
    msg = re.sub(r"\b\d+/\d+\b",                               "<RATIO>", msg)
    msg = re.sub(r"\b\d{3}\b",                                 "<STATUS>",msg)
    msg = re.sub(r"\b\d+\b",                                   "<NUM>",   msg)
    msg = re.sub(r"\s+",                                        " ",       msg).strip()
    return msg


templates: dict[str, int] = {}
token_ids: list[int] = []
for msg in df_logs["message"]:
    tmpl = mine_template(msg)
    if tmpl not in templates:
        templates[tmpl] = len(templates)
    token_ids.append(templates[tmpl])

df_logs["template"] = [mine_template(m) for m in df_logs["message"]]
df_logs["token_id"] = token_ids

vocab_df = pd.DataFrame(
    [(tid, tmpl) for tmpl, tid in templates.items()],
    columns=["token_id", "template"],
).sort_values("token_id").reset_index(drop=True)

# id2tmpl used by both the frequency plot and the e2e trace
id2tmpl = {v: k for k, v in templates.items()}

print(f"\n=== Vocabulary ({len(vocab_df)} templates) ===")
print(vocab_df.to_string(index=False))


# ── 2b. Template Frequency Distribution ───────────────────────────────────────

freq = df_logs["token_id"].value_counts().sort_index()
short_labels = [f"T{i}" for i in freq.index]
# Colour bars by whether any log carrying that token is anomalous
token_is_anomaly = df_logs.groupby("token_id")["label"].max()
bar_colors = ["#d62728" if token_is_anomaly.get(i, 0) == 1 else "#4878d0"
              for i in freq.index]

fig_freq, ax_freq = plt.subplots(figsize=(10, 3))
bars = ax_freq.bar(short_labels, freq.values, color=bar_colors,
                   edgecolor="black", linewidth=0.6)
for bar, count in zip(bars, freq.values):
    ax_freq.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 str(count), ha="center", va="bottom", fontsize=9)

ax_freq.set_xlabel("Template (Token ID)", fontsize=11)
ax_freq.set_ylabel("Occurrences", fontsize=11)
ax_freq.set_title("Template Frequency Distribution", fontsize=13, fontweight="bold")
ax_freq.set_ylim(0, freq.max() + 0.7)
ax_freq.grid(axis="y", alpha=0.3)

legend_patches = [
    mpatches.Patch(color="#4878d0", label="Normal template"),
    mpatches.Patch(color="#d62728", label="Anomaly template"),
]
ax_freq.legend(handles=legend_patches, fontsize=9)

# Add short template text as x-tick annotations
ax_freq.set_xticklabels(
    [f"T{i}\n{id2tmpl.get(i,'')[:18]}" for i in freq.index],
    fontsize=7,
)

plt.tight_layout()
plt.savefig("notebooks/token_freq_plot.png", dpi=120)
print("\nFrequency plot saved to notebooks/token_freq_plot.png")
plt.show()


# ── 3. Sliding Window Sequences ───────────────────────────────────────────────
# window_size=3 ensures multiple windows even with only 5 events per service.

WINDOW_SIZE = 3
STRIDE = 1


def build_windows(events: list[tuple[int, int]], window_size: int = 3, stride: int = 1) -> list[dict]:
    windows = []
    for start in range(0, len(events) - window_size + 1, stride):
        chunk = events[start : start + window_size]
        tokens = [e[0] for e in chunk]
        labels = [e[1] for e in chunk]
        windows.append({
            "window_idx":    len(windows),
            "tokens":        tokens,
            "any_anomaly":   int(any(l == 1 for l in labels)),
            "anomaly_count": sum(labels),
        })
    return windows


all_windows: list[dict] = []
for service, grp in df_logs.groupby("service", sort=False):
    events = list(zip(grp["token_id"], grp["label"]))
    wins = build_windows(events, WINDOW_SIZE, STRIDE)
    for w in wins:
        w["service"] = service
    all_windows.extend(wins)

df_windows = pd.DataFrame(all_windows).reset_index(drop=True)
print(f"\n=== Windows: {len(df_windows)} total (window_size={WINDOW_SIZE}, stride={STRIDE}) ===")
print(df_windows[["service", "tokens", "anomaly_count", "any_anomaly"]].to_string())


# ── 4. Anomaly Scoring ────────────────────────────────────────────────────────

VOCAB_SIZE = len(vocab_df)


def window_to_features(tokens: list[int]) -> np.ndarray:
    """Token frequency counts + Shannon entropy."""
    counts = np.zeros(VOCAB_SIZE, dtype=np.float32)
    for t in tokens:
        if 0 <= t < VOCAB_SIZE:
            counts[t] += 1
    total = counts.sum() or 1.0
    freqs = counts / total
    entropy = float(-np.sum(freqs[freqs > 0] * np.log2(freqs[freqs > 0])))
    return np.append(counts, entropy)


X = np.array([window_to_features(row["tokens"]) for _, row in df_windows.iterrows()])
print(f"\nFeature matrix: {X.shape}")

if SKLEARN_AVAILABLE:
    iso = IsolationForest(n_estimators=50, contamination=0.3, random_state=42)
    iso.fit(X)
    raw_scores = -iso.score_samples(X)
    method = "IsolationForest (sklearn)"
else:
    token_counts = X[:, :VOCAB_SIZE].sum(axis=0)
    rare_mask = (token_counts <= 1).astype(float)
    raw_scores = X[:, :VOCAB_SIZE].dot(rare_mask) + X[:, -1]
    method = "Deterministic mock (no sklearn)"

df_windows["raw_score"] = raw_scores
print(f"Scoring method : {method}")
print(f"Score range    : [{raw_scores.min():.4f}, {raw_scores.max():.4f}]")


# ── 5. Risk Score Normalization ───────────────────────────────────────────────

def min_max_normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi == lo:
        return np.full_like(arr, 0.5)
    return (arr - lo) / (hi - lo)


df_windows["risk_score"] = min_max_normalize(raw_scores)

print("\n=== Risk Scores ===")
print(df_windows[["service", "tokens", "any_anomaly", "raw_score", "risk_score"]]
      .round({"raw_score": 4, "risk_score": 3}).to_string())


# ── 6. Alert Policy ───────────────────────────────────────────────────────────

THRESHOLD    = 0.5
COOLDOWN_WIN = 2


def classify_severity(risk: float, thr: float) -> str:
    ratio = risk / thr if thr > 0 else 0
    if ratio >= 1.8: return "CRITICAL"
    if ratio >= 1.4: return "HIGH"
    if ratio >= 1.0: return "MEDIUM"
    return "none"


last_alert_win: dict[str, int] = {}
decisions: list[dict] = []

for _, row in df_windows.iterrows():
    svc  = row["service"]
    widx = row["window_idx"]
    risk = row["risk_score"]
    above = risk >= THRESHOLD

    in_cooldown = False
    if svc in last_alert_win:
        in_cooldown = (widx - last_alert_win[svc]) <= COOLDOWN_WIN

    fires = above and not in_cooldown
    if fires:
        last_alert_win[svc] = widx

    severity = classify_severity(risk, THRESHOLD) if fires else "none"

    decisions.append({
        "win_id":      widx,
        "service":     svc,
        "risk_score":  round(risk, 3),
        "above_thr":   above,
        "in_cooldown": in_cooldown,
        "alert_fires": fires,
        "severity":    severity,
        "true_label":  row["any_anomaly"],
    })

df_decisions = pd.DataFrame(decisions)
print(f"\n=== Alert Decisions (threshold={THRESHOLD}) ===")
print(f"Alerts fired: {df_decisions['alert_fires'].sum()} / {len(df_decisions)}")
print(df_decisions.to_string(index=False))


# ── 7. End-to-End Trace ───────────────────────────────────────────────────────
# This trace shows how a single window is transformed from tokens into model
# features and finally into an alert decision.

alert_rows = df_decisions[df_decisions["alert_fires"]]
highlight_win = int(alert_rows.iloc[0]["win_id"]) if not alert_rows.empty \
    else int(df_windows["risk_score"].idxmax())

win_row = df_windows.loc[highlight_win]
dec_row = df_decisions[df_decisions["win_id"] == win_row["window_idx"]].iloc[0]
tok_list = win_row["tokens"]

print("\n" + "=" * 62)
print("  END-TO-END TRACE")
print("=" * 62)
print(f"Service    : {win_row['service']}")
print(f"Window ID  : {highlight_win}  ({len(tok_list)} events)\n")
print("STEP 1 — Tokens in window:")
for idx, tid in enumerate(tok_list):
    print(f"  [{idx}] token_id={tid}  template: {id2tmpl.get(tid, '?')}")

features = window_to_features(tok_list)
print(f"\nSTEP 2 — Feature shape: {features.shape}")
print(f"         Non-zero dims : {int((features[:VOCAB_SIZE] > 0).sum())}")
print(f"         Entropy       : {features[-1]:.4f}")
print(f"\nSTEP 3 — Raw score   : {win_row['raw_score']:.4f}")
print(f"STEP 4 — Risk score  : {win_row['risk_score']:.3f}")
print(f"\nSTEP 5 — Above thr   : {dec_row['above_thr']}")
print(f"         In cooldown  : {dec_row['in_cooldown']}")
print(f"         Alert fires  : {dec_row['alert_fires']}")
print(f"         Severity     : {dec_row['severity']}")
print(f"         True label   : {'ANOMALY' if dec_row['true_label'] else 'normal'}")
print("=" * 62)


# ── 8. Risk Score Plot ────────────────────────────────────────────────────────

COLORS = {
    "CRITICAL": "#d62728",
    "HIGH":     "#ff7f0e",
    "MEDIUM":   "#ffdd57",
    "none":     "#aec7e8",
}

fig, ax = plt.subplots(figsize=(12, 5))

for _, row in df_decisions.iterrows():
    sev   = row["severity"]
    color = COLORS.get(sev, "#aec7e8")
    ax.bar(row["win_id"], row["risk_score"], color=color,
           edgecolor="black", linewidth=0.5, width=0.7)

# Threshold line
ax.axhline(THRESHOLD, color="red", linestyle="--", linewidth=1.8,
           zorder=5, label=f"Alert threshold = {THRESHOLD}")

# X markers on true anomaly windows
for _, row in df_decisions.iterrows():
    if row["true_label"] == 1:
        ax.annotate("x", xy=(row["win_id"], row["risk_score"] + 0.04),
                    ha="center", va="bottom", fontsize=14,
                    color="black", fontweight="bold")
    ax.text(row["win_id"], 0.02, row["service"][:3].upper(),
            ha="center", va="bottom", fontsize=7, color="dimgrey")

# Legend: only show severity colours that actually appear
present_sevs = df_decisions["severity"].unique()
patches = [mpatches.Patch(color=COLORS[s], label=f"Alert: {s}")
           for s in ["CRITICAL", "HIGH", "MEDIUM", "none"] if s in present_sevs]
patches.append(plt.Line2D([0], [0], color="red", linestyle="--",
                           label=f"Threshold = {THRESHOLD}"))
patches.append(plt.Line2D([0], [0], marker=None, color="none",
                           label="X = true anomaly window"))
ax.legend(handles=patches, loc="upper right", fontsize=10, framealpha=0.9)

ax.set_xlabel("Window ID", fontsize=12)
ax.set_ylabel("Risk Score (0 - 1)", fontsize=12)
ax.set_title("Anomaly Risk Score per Sliding Window", fontsize=14,
             fontweight="bold", pad=12)
ax.set_ylim(0, 1.18)
ax.set_xticks(df_decisions["win_id"])
ax.grid(axis="y", alpha=0.3, linestyle=":")

plt.tight_layout()
plt.savefig("notebooks/risk_score_plot.png", dpi=120)
print("\nRisk score plot saved to notebooks/risk_score_plot.png")
plt.show()

print("\nDemo complete.")
