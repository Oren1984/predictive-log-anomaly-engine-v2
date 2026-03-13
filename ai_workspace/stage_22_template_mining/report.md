# Stage 22 Template Mining Report

**Generated:** 2026-03-03  
**Execution time:** 9.2s  
**Input:** `events_sample_1m.csv`  

---

## Summary

| Metric | Value |
|--------|------:|
| Input rows | 1,000,000 |
| Unique templates | 7,833 |
| Avg rows / template | 127.7 |
| Generalization time | 3.9s |
| Total elapsed | 9.2s |
| Peak memory | 467.9 MB |
| Input file size | 166.7 MB |
| Output CSV size | 266.3 MB |
| Templates CSV size | 1.47 MB |

---

## Token Substitution Pipeline

| Step | Pattern | Token |
|-----:|---------|-------|
| 1 | Block IDs: `blk_-?\\d+` | `<BLK>` |
| 2 | BGL datetime: `\\d{4}-\\d{2}-\\d{2}-\\d{2}\\.\\d{2}\\.\\d{2}\\.\\d+` | `<TS>` |
| 3 | IP address: `\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}(?::\\d+)?` | `<IP>` |
| 4 | BGL date: `\\d{4}\\.\\d{2}\\.\\d{2}` | `<DATE>` |
| 5 | BGL node ID: `R\\d+(?:-[A-Z\\d]+)+(?::[A-Z]\\d+-[A-Z]\\d+)?` | `<NODE>` |
| 6 | File path: `/[a-zA-Z0-9_./\\-]+` | `<PATH>` |
| 7 | Hex string: `\\b[0-9a-f]{8,}\\b` | `<HEX>` |
| 8 | Integer: `\\b\\d+\\b` | `<NUM>` |
| 9 | Whitespace: `\\s+` | `` `` |

---

## Per-Dataset Template Counts

| Dataset | Unique Templates |
|---------|----------------:|
| bgl | 7,792 |
| hdfs | 41 |

---

## Template Frequency Distribution

| Frequency bucket | # Templates |
|------------------|------------:|
| 0 | 5,319 |
| 1 | 911 |
| 2-4 | 713 |
| 5-9 | 262 |
| 10-49 | 414 |
| 50-99 | 65 |
| 100-499 | 98 |
| 500-999 | 15 |
| 1k-4k | 16 |
| 5k-9k | 7 |
| 10k+ | 13 |

---

## Top 20 Templates by Frequency

| Rank | TID | Count | Anomaly Rate | Template (first 120 chars) |
|-----:|----:|------:|-------------:|---------------------------|
| 1 | 6675 | 108,159 | 2.75% | `<NUM> <NUM> <NUM> INFO dfs.DataNode$DataXceiver: Receiving block <BLK> src: /<IP> dest: /<IP>` |
| 2 | 5411 | 107,272 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO generating core.<NUM>` |
| 3 | 6684 | 106,808 | 1.88% | `<NUM> <NUM> <NUM> INFO dfs.DataNode$PacketResponder: PacketResponder <NUM> for block <BLK> terminating` |
| 4 | 6692 | 104,187 | 2.25% | `<NUM> <NUM> <NUM> INFO dfs.FSNamesystem: BLOCK* NameSystem.addStoredBlock: blockMap updated: <IP> is added to <BLK> size` |
| 5 | 6685 | 103,845 | 1.71% | `<NUM> <NUM> <NUM> INFO dfs.DataNode$PacketResponder: Received block <BLK> of size <HEX> from /<IP>` |
| 6 | 6689 | 88,215 | 2.52% | `<NUM> <NUM> <NUM> INFO dfs.FSDataset: Deleting block <BLK> file <PATH><BLK>` |
| 7 | 6695 | 87,724 | 2.26% | `<NUM> <NUM> <NUM> INFO dfs.FSNamesystem: BLOCK* NameSystem.delete: <BLK> is added to invalidSet of <IP>` |
| 8 | 6694 | 36,256 | 2.73% | `<NUM> <NUM> <NUM> INFO dfs.FSNamesystem: BLOCK* NameSystem.allocateBlock: <PATH> <BLK>` |
| 9 | 5412 | 27,808 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO iar <HEX> dear <HEX>` |
| 10 | 6672 | 26,848 | 2.75% | `<NUM> <NUM> <NUM> INFO dfs.DataNode$DataXceiver: <IP> Served block <BLK> to /<IP>` |
| 11 | 6701 | 22,336 | 2.36% | `<NUM> <NUM> <NUM> WARN dfs.DataNode$DataXceiver: <IP>:Got exception while serving <BLK> to /<IP>:` |
| 12 | 1729 | 16,188 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO <NUM> floating point alignment exceptions` |
| 13 | 1728 | 11,077 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO <NUM> double-hummer alignment exceptions` |
| 14 | 6722 | 9,526 | 0.00% | `KERNDTLB <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL FATAL data TLB error interrupt` |
| 15 | 1757 | 8,496 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO <NUM> total interrupts. <NUM> critical input interrupts. <NUM> microse` |
| 16 | 1730 | 8,442 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO <NUM> microseconds spent in the rbs signal handler during <NUM> calls.` |
| 17 | 6664 | 7,646 | 2.62% | `<NUM> <NUM> <NUM> INFO dfs.DataBlockScanner: Verification succeeded for <BLK>` |
| 18 | 1713 | 7,627 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO <HEX> double-hummer alignment exceptions` |
| 19 | 5415 | 6,660 | 100.00% | `- <HEX> <DATE> <NODE> <TS> <NODE> RAS KERNEL INFO instruction cache parity error corrected` |
| 20 | 5438 | 5,248 | 100.00% | `- <HEX> <DATE> NULL <TS> NULL RAS MMCS ERROR idoproxydb hit ASSERT condition: ASSERT expression=<NUM> Source file=idotra` |

---

## Output Files

| File | Rows | Size |
|------|-----:|-----:|
| `events_with_templates.csv` | 1,000,000 | 266.3 MB |
| `templates.csv` | 7,833 | 1.47 MB |

---

*Stage 22 completed successfully.*
