# EXL3 4bpw — key settings

Two GB10 nodes, tensor-parallel 2. Recipe:
[MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks).

## Weights

| | |
|---|---|
| Model | `Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw` |
| Drafter | `incoai/GLM-5.3-Flash-DFlash2` |

## Environment

```
TP=2
NNODES=2
QUANTIZATION=exl3
ENFORCE_EAGER=0                 # CUDA graphs ON -- leave it on
EXL3_FUSED_MOE=1                # fused exllamav3_ext.exl3_moe per layer
EXL3_TEMP_ROWS_FUSED=128        # 1024 lost the A/B upstream; keep 128
EXL3_MOE_ROW_TILE=0

SPEC_METHOD=dflash
DFLASH_TOKENS=7
MTP_TOKENS=2

MAX_MODEL_LEN=1000000           # 1,754,237-token pool, 1.75x at 1M
MAX_NUM_SEQS=4
MAX_NUM_BATCHED_TOKENS=2048     # 8192 oversubscribes the GB10 indexer topk
GPU_MEM_UTIL=0.87
KV_CACHE_DTYPE=fp8

DFLASH_DRAFT_TP=2               # shard drafter across ranks: +37% per-stream at C4
GLM53_MIXED_PREFILL_CHUNK=skip
GLM53_SUPPRESS_STOPS_IN_REASONING=1
LIMIT_MM='{"image":4,"video":1}'
SKIP_MM_PROFILING=1
```

## `DFLASH_DRAFT_TP`

Upstream default became `2` on 2026-08-30. Measured here: **+37% per-stream at C4**
(26.7 → 36.6 tok/s), +16% at C1, and −18% KV pool (1.75× → 1.44× at 1M). Their own
single-stream gain did not reproduce for us — we measure a small regression on
`bench_decode.py` (structured 64.3 → 63.2, prose 26.6 → 25.4).

Take it if you serve concurrent sessions. Roll back with `DFLASH_DRAFT_TP=1` if you
are pool-constrained or run strictly single-stream. See the README and
[upstream issue #56](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/issues/56).

## Gotchas

- **Thinking is ON by default.** Our first benchmark pass returned 1024 tokens and
  **zero visible characters** — the whole budget went to reasoning. Pass
  `chat_template_kwargs: {"enable_thinking": false}` for a like-for-like comparison
  against an engine that defaults to thinking off. This single setting invalidates
  most cross-recipe throughput comparisons you will read, including ours if we had
  missed it.
- **Quote `LIMIT_MM` exactly as shown.** Dropping the single quotes lets the shell
  strip the inner double quotes, producing invalid JSON and killing both ranks.
- **The published image can lag the repo.** Ours was a day behind its own `main`;
  the fix is a local `BUILD=1` rebuild, which compiles the `exllamav3` wheel and
  takes roughly 25-30 minutes.
- **`start.sh` refuses to build while the port is held.** Use `restart`, not
  `start`, when rebuilding a live deployment.
- **`GLM53_MIXED_PREFILL_CHUNK=skip`** is upstream's default and fine here, but the
  same setting starved live sessions on our other stack (`Running: 1 / Waiting: 5 /
  Deferred: 4`, generation 0.0 tok/s). Know what it does before copying it across
  engines.
