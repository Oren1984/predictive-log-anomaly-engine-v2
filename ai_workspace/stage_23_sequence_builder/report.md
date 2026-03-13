# Stage 23 (V2) Sequence Builder Report

**Generated:** 2026-03-03  
**Execution time:** 69.6s  
**Peak memory:** 1138.2 MB  

---

## Summary

| Metric | Value |
|--------|------:|
| Total sessions | 495,405 |
| Avg sequence length | 2.02 |
| Median sequence length | 2.0 |
| Max sequence length | 34 |
| Template vocabulary size | 7,833 |
| Unique bigrams (global) | 16,808 |
| Template feature cols (raw+norm) | 200 |
| Bigram feature cols (raw+norm) | 200 |
| Total feature cols | 407 |
| Execution time | 69.6s |
| Peak memory | 1138.2 MB |

---

## Label Distribution (session level)

| Label | Sessions | Pct |
|------:|---------:|----:|
| 0 | 400,897 | 80.92% |
| 1 | 94,508 | 19.08% |

---

## Dataset Distribution

| Dataset | Sessions | Pct |
|---------|--------:|----:|
| hdfs | 404,179 | 81.59% |
| bgl | 91,226 | 18.41% |

---

## Top 10 Longest Sessions

| session_id | dataset | label | sequence_length |
|------------|---------|------:|----------------:|
| blk_-2891794341254261063 | hdfs | 1 | 34 |
| blk_-5224041993350565248 | hdfs | 0 | 24 |
| blk_2866275036574950116 | hdfs | 0 | 24 |
| blk_-8333455052087360327 | hdfs | 0 | 22 |
| blk_-5375761801379702192 | hdfs | 1 | 20 |
| blk_5762192118127023083 | hdfs | 0 | 20 |
| blk_-6954586533193620247 | hdfs | 0 | 20 |
| blk_-7288708571822700018 | hdfs | 0 | 18 |
| blk_-442823578746301707 | hdfs | 0 | 18 |
| blk_-1016453873803095686 | hdfs | 0 | 18 |

---

## Top-100 Templates Selected (top 20 shown)

Total template columns: 100 raw + 100 norm

| Rank | Column | Total count across sessions |
|-----:|--------|--------------------------:|
| 1 | `tid_6675` | 108,159 |
| 2 | `tid_5411` | 107,272 |
| 3 | `tid_6684` | 106,808 |
| 4 | `tid_6692` | 104,187 |
| 5 | `tid_6685` | 103,845 |
| 6 | `tid_6689` | 88,215 |
| 7 | `tid_6695` | 87,724 |
| 8 | `tid_6694` | 36,256 |
| 9 | `tid_5412` | 27,808 |
| 10 | `tid_6672` | 26,848 |
| 11 | `tid_6701` | 22,336 |
| 12 | `tid_1729` | 16,188 |
| 13 | `tid_1728` | 11,077 |
| 14 | `tid_6722` | 9,526 |
| 15 | `tid_1757` | 8,496 |
| 16 | `tid_1730` | 8,442 |
| 17 | `tid_6664` | 7,646 |
| 18 | `tid_1713` | 7,627 |
| 19 | `tid_5415` | 6,660 |
| 20 | `tid_5438` | 5,248 |

---

## Top-100 Bigrams Selected (top 20 shown)

Total bigram columns: 100 raw + 100 norm  
Total unique bigrams globally: 16,808

| Rank | Bigram (column) | Total count across sessions |
|-----:|----------------|--------------------------:|
| 1 | `bgram_5411_to_5411` | 73,863 |
| 2 | `bgram_5412_to_5412` | 18,496 |
| 3 | `bgram_1729_to_1729` | 10,615 |
| 4 | `bgram_1728_to_1728` | 7,384 |
| 5 | `bgram_6684_to_6675` | 7,310 |
| 6 | `bgram_6675_to_6684` | 7,191 |
| 7 | `bgram_6692_to_6675` | 7,151 |
| 8 | `bgram_6692_to_6685` | 7,106 |
| 9 | `bgram_6685_to_6684` | 7,024 |
| 10 | `bgram_6685_to_6675` | 7,018 |
| 11 | `bgram_6675_to_6692` | 7,015 |
| 12 | `bgram_6685_to_6692` | 7,011 |
| 13 | `bgram_6692_to_6684` | 6,985 |
| 14 | `bgram_6684_to_6692` | 6,983 |
| 15 | `bgram_6675_to_6685` | 6,939 |
| 16 | `bgram_6684_to_6685` | 6,820 |
| 17 | `bgram_6722_to_6722` | 6,557 |
| 18 | `bgram_6689_to_6684` | 5,904 |
| 19 | `bgram_6684_to_6695` | 5,873 |
| 20 | `bgram_6689_to_6675` | 5,860 |

---

## Output Files

| File | Shape |
|------|-------|
| `session_sequences_v2.csv` | 495,405 rows x 6 cols |
| `session_features_v2.csv`  | 495,405 rows x 407 cols |

---

*Stage 23 (v2) completed successfully.*
