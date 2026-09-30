# GLM-5.3-Flash EXL3 TP=4 decode, 2026-09-30

`tests/bench_decode.py` (byte-identical between the two recipe commits), 8 runs x 400 tok,
temp 0, thinking off, direct to the engine, idle. `MODEL` set to the served name.

| dir | recipe | engine state |
|---|---|---|
| `before/` | `94ae731` | up ~11 h, 4-6 GB swapped per node |
| `after/`  | `674155d` | fresh boot, 0 swap, `EXL3_FAT_GROUPED=1` |

Cells: `structured-x1`, `code-x1`, `prose-x1`, `structured-x2`, `structured-x4`. Per-run tok/s
is `runs[].tok_s`; `aggregate_tok_s_median` is tokens over wall time (not a sum of stream
rates). The TP=2 comparison arm is `../moe-fast-ab-20260918/A/`.
