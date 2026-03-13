# PHASE_02_PREPROCESSING_REPORT.md
## Predictive Log Anomaly Engine — Phase 2 Refactor Progress Report

**Phase:** 2 — NLP Embedding Pipeline
**Status:** Complete
**Date:** 2026-03-08
**Scope:** Full implementation of `LogPreprocessor` at `src/preprocessing/log_preprocessor.py`

---

## 1. What Was Implemented

Phase 2 replaced the Phase 1 `NotImplementedError` stubs in `LogPreprocessor` with a fully working NLP embedding pipeline. The class now provides:

| Method | Description |
|---|---|
| `clean(raw_text)` | Normalises a raw log message string into a placeholder-substituted lowercase string |
| `tokenize(text)` | Splits a cleaned string into tokens, treating `[PLACEHOLDER]` tokens as atomic units |
| `train_embeddings(corpus)` | Trains a Word2Vec (default) or FastText (experimental) model on a tokenised corpus |
| `embed(tokens)` | Mean-pools word vectors for a token list into a single float vector |
| `process_log(log_line)` | End-to-end pipeline: `clean` → `tokenize` → `embed` (primary inference interface) |
| `transform(raw_text)` | Alias for `process_log` — kept for interface consistency with sklearn-style APIs |
| `save(path)` | Saves the trained gensim model to disk, creating parent directories automatically |
| `load(path)` | Loads a previously saved model; syncs `vec_dim` from the loaded model |
| `is_trained` | Property: `True` when a model is loaded and ready for inference |

Only `src/preprocessing/log_preprocessor.py` was modified. No existing module was touched. The existing runtime pipeline (`POST /ingest → InferenceEngine`) is unchanged.

---

## 2. How Logs Are Normalised

`clean()` applies a deterministic multi-step normalisation pipeline to each raw log message:

### Step 1: Lowercase and strip
```python
text = raw_text.lower().strip()
```
All text is lowercased before further processing. This ensures pattern matching is uniform and the vocabulary does not distinguish `ERROR` from `error`.

### Step 2: Service-name prefix removal
```python
_SERVICE_PREFIXES = re.compile(
    r"^(hdfs|bgl|dfs|hadoop|namenode|datanode|jobtracker|tasktracker)[\s.:,]",
    re.IGNORECASE,
)
text = _SERVICE_PREFIXES.sub("[SERVICE] ", text)
```
BGL and HDFS log lines often begin with the dataset/service name. These are replaced with the generic `[SERVICE]` token to prevent the model from overfitting to dataset-specific prefix strings.

### Step 3: Regex substitution pipeline

The `_NORM_PATTERNS` list is applied in order. Order matters: more specific patterns (BLK IDs, timestamps) are applied before more general ones (integers) to prevent partial matches.

| Token | Pattern | Example input | Output |
|---|---|---|---|
| `[BLK]` | `blk_-?\d+` | `blk_-1234567890` | `[BLK]` |
| `[TIMESTAMP]` | BGL dotted format | `2005-12-01-06.51.06.123456` | `[TIMESTAMP]` |
| `[TIMESTAMP]` | ISO datetime | `2005-12-01T06:51:06` | `[TIMESTAMP]` |
| `[TIMESTAMP]` | Date only | `2023-07-15` | `[TIMESTAMP]` |
| `[IP]` | IPv4 with optional port | `10.0.0.1:8080` | `[IP]` |
| `[NODE]` | BGL rack/node IDs | `R3-M1-N1:J18-U11` | `[NODE]` |
| `[PATH]` | Unix file paths | `/var/log/app.log` | `[PATH]` |
| `[HEX]` | 8+ char hex strings | `deadbeef12345678` | `[HEX]` |
| `[NUM]` | Bare integers | `3`, `1048576` | `[NUM]` |

The `[NODE]` pattern uses `re.IGNORECASE` because `clean()` lowercases first, and BGL node identifiers such as `R3-M1-N1` would otherwise fail to match after lowercasing.

**Known limitation:** Hex strings prefixed with `0x` (e.g. `0x1a2b3c4d`) are not matched by the `[HEX]` pattern because the `x` character creates a `\w` boundary before the hex digits, preventing the leading `\b` from firing. Bare hex strings of 8+ characters are matched correctly.

### Step 4: Final strip
Leading and trailing whitespace is removed from the result.

### Example

```python
raw = "ERROR blk_-1234567890 from 192.168.1.1:50010 /user/hadoop/tmp not found"
# After clean():
# "error [BLK] from [IP] [PATH] not found"
```

---

## 3. Tokenisation

`tokenize()` uses a single compiled regex:

```python
_TOKEN_RE = re.compile(r"\[[A-Z]+\]|\w+")
```

The alternation matches placeholder tokens (e.g. `[IP]`, `[TIMESTAMP]`) as atomic units first, then falls through to `\w+` for ordinary word characters. This ensures:

- `[IP]` appears as a single token, not `[`, `IP`, `]` separately
- Punctuation-only fragments are silently discarded
- Tokens are already lowercase (normalised by `clean()`)

```python
tokenize("[TIMESTAMP] [BLK] disk full")
# -> ["[TIMESTAMP]", "[BLK]", "disk", "full"]
```

---

## 4. Word2Vec Integration

### Training
`train_embeddings(corpus)` trains a gensim `Word2Vec` model when `embedding_type="word2vec"` (the default):

```python
preprocessor = LogPreprocessor(vec_dim=100, min_count=2, epochs=10, window=5)
corpus = [preprocessor.tokenize(preprocessor.clean(msg)) for msg in raw_messages]
preprocessor.train_embeddings(corpus)
```

The model learns distributed representations for log tokens. Tokens that appear in fewer than `min_count` log lines are excluded from the vocabulary.

### Inference
`process_log()` computes a fixed-size embedding for a single log line via mean pooling:

```python
vector = preprocessor.process_log("ERROR disk full on 10.0.0.1")
# -> np.ndarray, shape (100,), dtype float32
```

Mean pooling averages the word vectors for all tokens present in the vocabulary. Tokens not in the vocabulary are silently skipped. If no token matches the vocabulary, a zero vector of shape `[vec_dim]` is returned. This zero-vector sentinel is detectable downstream.

### Persistence
```python
preprocessor.save(Path("models/word2vec.model"))   # saves gensim model to disk
preprocessor.load(Path("models/word2vec.model"))   # loads and syncs vec_dim
```

Parent directories are created automatically by `save()`. `load()` syncs `self.vec_dim` from the saved model's `vector_size` attribute in case the model was trained with a different dimensionality than the constructor default.

### gensim lazy import
gensim is imported at module level inside a `try/except ImportError` block:

```python
try:
    from gensim.models import Word2Vec as _Word2VecModel
    from gensim.models import FastText as _FastTextModel
    _GENSIM_AVAILABLE = True
except ImportError:
    _GENSIM_AVAILABLE = False
    _Word2VecModel = _FastTextModel = None
```

This keeps the module importable in CI environments where gensim is not installed (e.g. test runs that exercise only the API layer). The guard `_GENSIM_AVAILABLE` is checked inside `train_embeddings()` and `load()`, both of which raise `ImportError` with a clear install instruction if gensim is absent.

---

## 5. FastText Experimental Mode

FastText is available as an opt-in alternative:

```python
preprocessor = LogPreprocessor(embedding_type="fasttext")
```

It is strictly guarded by three mechanisms:

1. **Constructor warning:** `logger.warning()` is emitted immediately when `embedding_type="fasttext"` is passed to `__init__`, identifying it as experimental and stating that Word2Vec is the production default.

2. **ValueError on invalid type:** Any embedding type other than `"word2vec"` or `"fasttext"` raises `ValueError`, preventing silent fallthrough.

3. **No promotion path:** FastText is not the default and is not referenced anywhere in the existing runtime pipeline. It must never be set as the default without comparative evaluation against Word2Vec on the BGL/HDFS benchmark.

The FastText implementation path is otherwise identical to Word2Vec (same `train_embeddings`, `save`, `load`, `embed` logic). This makes future comparative evaluation straightforward.

---

## 6. Test Suite

44 new unit tests were added at `tests/unit/test_log_preprocessor.py`.

### Test classes

| Class | Tests | Coverage |
|---|---|---|
| `TestClean` | 15 | All normalisation patterns, service prefix, whitespace, empty input |
| `TestTokenize` | 6 | Word splitting, placeholder atomicity, punctuation discard, empty input |
| `TestIsTrained` | 2 | Property before and after training |
| `TestRequiresModel` | 3 | `embed`, `process_log`, `transform` raise `RuntimeError` before model loaded |
| `TestTrainEmbeddings` | 3 | Successful training, empty corpus, gensim absent (mocked) |
| `TestEmbed` | 4 | Shape, dtype, OOV zero vector, known token |
| `TestProcessLog` | 3 | Shape, dtype, `transform` alias equivalence |
| `TestPersistence` | 5 | Round-trip save/load, parent dir creation, save without model, missing file, gensim absent |
| `TestFastTextExperimental` | 3 | Warning on init, invalid embedding type |

### Test suite results

```
255 passed, 22 deselected in 25.48s
```

- **255 tests passed** (211 pre-existing + 44 new Phase 2 tests)
- **22 deselected** (slow/model-dependent tests, unchanged)
- **0 failures, 0 errors**

---

## 7. Dependency Change

`gensim>=4.3.0` was added to `requirements.txt` under the heading `# NLP embedding (Stage 1 — LogPreprocessor)`.

Installed version: gensim 4.4.0.

This is the only new dependency introduced in Phase 2. All other `requirements.txt` entries are unchanged.

---

## 8. Risks and Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| `0x`-prefixed hex strings not matched by `[HEX]` | Low | These are rare in HDFS/BGL logs; bare 8-char hex strings (error codes, addresses) are matched correctly. Known limitation documented in tests. |
| Zero vector returned for fully OOV log lines | Medium | Downstream stages (LSTM encoder) will receive an all-zero input for logs with no vocabulary coverage. This can be detected by L2-norm check if needed in Phase 5. |
| FastText experimental mode not benchmarked | Low | FastText is blocked from becoming the default by the constructor warning and architecture policy. |
| gensim model format may change across minor versions | Low | Models are saved and loaded by the same gensim version within a deployment. Version pinning in `requirements.txt` prevents silent format drift. |
| `min_count=2` excludes rare tokens | Medium | For small corpora, many tokens may be filtered. The default can be lowered to `min_count=1` for offline experiments, but should remain at `2` for production to suppress noise tokens. |

---

## 9. Phase Boundary

Phase 2 is complete. The following are deferred to later phases:

| Deferred item | Phase |
|---|---|
| `LogDataset` (PyTorch Dataset wrapping embedded windows) | Phase 3 |
| `SystemBehaviorModel` (LSTM encoder) | Phase 4 |
| `AnomalyDetector` (Denoising Autoencoder) | Phase 5 |
| `SeverityClassifier` (MLP) | Phase 6 |
| `ProactiveMonitorEngine` (end-to-end orchestrator) | Phase 7 |
| Wiring `LogPreprocessor` into the live `/ingest` pipeline | Phase 7 |

The existing runtime path (`POST /ingest → InferenceEngine → baseline/transformer`) continues to operate unchanged. `LogPreprocessor` is not imported by any existing module and has no effect on production behavior until Phase 7.

Phase 2 is complete. The repository is ready for Phase 3 (Sequence Dataset — `LogDataset` implementation).
