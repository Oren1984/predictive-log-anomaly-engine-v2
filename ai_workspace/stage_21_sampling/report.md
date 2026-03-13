# Stage 21 Sampling Report

**Generated:** 2026-03-03  
**Execution time:** 41.8s  
**Random seed:** 42  
**Stratified by:** `label`, `dataset`  

---

## Summary

| Metric | Value |
|--------|-------|
| Input file | `events_unified.csv` |
| Total input rows | 15,923,592 |
| Sampled rows | 1,000,000 |
| Sampling fraction | 6.2800% |
| Input file size | 2654.7 MB |
| Output file size | 166.7 MB |
| Peak process memory | 833.1 MB |
| Execution time | 41.8s |

---

## Label Distribution

| Label | Count | Fraction |
|-------|------:|----------:|
| 0 | 705,609 | 70.5609% |
| 1 | 294,391 | 29.4391% |

---

## Dataset Distribution

| Dataset | Count | Fraction |
|---------|------:|----------:|
| bgl | 298,171 | 29.8171% |
| hdfs | 701,829 | 70.1829% |

---

## Per-Group Sample Details

| Label | Dataset | Input Rows | Sampled Rows | Fraction |
|------:|---------|----------:|-------------:|----------:|
| 0 | bgl | 348,460 | 21,883 | 6.2799% |
| 0 | hdfs | 10,887,379 | 683,726 | 6.2800% |
| 1 | bgl | 4,399,503 | 276,288 | 6.2800% |
| 1 | hdfs | 288,250 | 18,103 | 6.2803% |

---

## Top 20 Frequent Messages

| Rank | Count | Message (first 120 chars) |
|-----:|------:|--------------------------|
| 1 | 2 | `081110 224547 16426 INFO dfs.DataNode$PacketResponder: Received block blk_-6502650234896412734 of size 67108864 from /10` |
| 2 | 2 | `081109 204637 556 INFO dfs.DataNode$PacketResponder: Received block blk_-6320089668124629180 of size 67108864 from /10.2` |
| 3 | 2 | `081110 115344 10650 INFO dfs.DataNode$PacketResponder: Received block blk_767006533341077224 of size 67108864 from /10.2` |
| 4 | 2 | `081110 111018 9813 INFO dfs.DataNode$PacketResponder: Received block blk_-6550889247426673720 of size 67108864 from /10.` |
| 5 | 2 | `081110 220659 18 INFO dfs.FSDataset: Deleting block blk_-9172947514522041361 file /mnt/hadoop/dfs/data/current/subdir52/` |
| 6 | 2 | `081109 212415 2016 INFO dfs.DataNode$PacketResponder: Received block blk_-3349975077663956198 of size 67108864 from /10.` |
| 7 | 2 | `081110 103630 19 INFO dfs.FSDataset: Deleting block blk_-2319428880642351841 file /mnt/hadoop/dfs/data/current/blk_-2319` |
| 8 | 1 | `- 1133448666 2005.12.01 R60-M1-NC-C:J12-U01 2005-12-01-06.51.06.840240 R60-M1-NC-C:J12-U01 RAS KERNEL INFO 0 microsecond` |
| 9 | 1 | `081110 010510 30 INFO dfs.FSNamesystem: BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.37.240:50010 is added` |
| 10 | 1 | `081111 075616 28 INFO dfs.FSNamesystem: BLOCK* NameSystem.delete: blk_-3584151299152942241 is added to invalidSet of 10.` |
| 11 | 1 | `081111 052617 21200 INFO dfs.DataNode$PacketResponder: Received block blk_-3337674171004867062 of size 67108864 from /10` |
| 12 | 1 | `081109 220443 3266 WARN dfs.DataNode$DataXceiver: 10.251.202.134:50010:Got exception while serving blk_-4251337463767332` |
| 13 | 1 | `081110 103315 19 INFO dfs.FSDataset: Deleting block blk_-8722912542535385865 file /mnt/hadoop/dfs/data/current/subdir44/` |
| 14 | 1 | `- 1118772482 2005.06.14 R27-M0-N8-C:J13-U01 2005-06-14-11.08.02.821424 R27-M0-N8-C:J13-U01 RAS KERNEL FATAL 12:28244842 ` |
| 15 | 1 | `- 1118770217 2005.06.14 R27-M0-N6-C:J08-U11 2005-06-14-10.30.17.669045 R27-M0-N6-C:J08-U11 RAS KERNEL FATAL program inte` |
| 16 | 1 | `081109 223038 3519 WARN dfs.DataNode$DataXceiver: 10.251.39.209:50010:Got exception while serving blk_-25453833962370719` |
| 17 | 1 | `- 1118810026 2005.06.14 R02-M1-N0-C:J12-U11 2005-06-14-21.33.46.293461 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction c` |
| 18 | 1 | `081111 023245 19 INFO dfs.FSDataset: Deleting block blk_-2458797038559971394 file /mnt/hadoop/dfs/data/current/subdir62/` |
| 19 | 1 | `081111 030050 18256 INFO dfs.DataNode$DataXceiver: Receiving block blk_6916511691144210805 src: /10.251.35.1:51545 dest:` |
| 20 | 1 | `- 1122139670 2005.07.23 R05-M0-NA-C:J08-U01 2005-07-23-10.27.50.232455 R05-M0-NA-C:J08-U01 RAS KERNEL INFO 15 floating p` |

---

## Memory Estimation

Peak memory was measured using `psutil` on the live process.

- **Input file:** 2654.7 MB on disk
- **Output file:** 166.7 MB on disk
- **Peak RSS:** 833.1 MB
- **Chunk size:** 500,000 rows per chunk

> Two-pass chunked reading ensures the full input is never held
> in memory at once; only ~1M sampled rows accumulate between passes.

---

*Stage 21 completed successfully.*
