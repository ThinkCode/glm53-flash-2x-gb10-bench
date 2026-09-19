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
GLM53_MIXED_PREFILL_CHUNK=fair  # was skip -- skip starves newcomers for the whole incumbent generation; see README 2026-09-19
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
- **`GLM53_MIXED_PREFILL_CHUNK=skip` is NOT fine for shared serving** — we said the
  opposite here on 2026-08-31 and were wrong. It starved our own sessions on this
  stack (`run=1 wait=1` with 85% KV free; a one-liner waiting ~190 s behind an
  essay), exactly as it had on the other engine (`Running: 1 / Waiting: 5 /
  Deferred: 4`). Upstream changed its default to `fair` on 2026-09-15. Use `fair`.
  See the README's 2026-09-19 update.

## Live environment at the v1.5 reproduction (2026-09-17)

What actually served the numbers in the README's 2026-09-17 update. Differences
from the block above are upstream defaults moving, not tuning on our side, except
where noted.

```
IMAGE=ghcr.io/miaai-lab/glm-5.3-flash-2x-dgx-sparks:exl3-instanttensor
MODEL=Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw
MODEL_REVISION=25a44fdbf16862a46b7cc9921142c6c81350af2f
DFLASH_MODEL=incoai/GLM-5.3-Flash-DFlash2
DFLASH_REVISION=dc77ff1c99eeb2df044ee3d4f0094eb033fee410
DFLASH_TOKENS=7
DFLASH_DRAFT_TP=2
MTP_TOKENS=2

MAX_MODEL_LEN=850000            # upstream default moved 1M -> 850k
MAX_NUM_SEQS=4
MAX_NUM_BATCHED_TOKENS=7168     # upstream maintainer default at MAX_NUM_SEQS=4
GLM53_INDEXER_WORKSPACE=rightsize
GPU_MEM_UTIL=0.89               # OURS; upstream default is 0.85
KV_CACHE_DTYPE=fp8
ENFORCE_EAGER=0
EXL3_FUSED_MOE=1
EXL3_FAT_GROUPED=1
# EXL3_FAT_KERNEL unset -> start.sh default 1 (E2/E3 fat-expert kernel on)

GLM53_MIXED_PREFILL_CHUNK=skip  # WRONG for shared serving -- changed to fair 2026-09-19, see README
GLM53_DEFAULT_REASONING_EFFORT=low   # OURS; upstream leaves empty
GLM53_BOOT_SHAPE_WARMUP=1
GLM53_SUPPRESS_STOPS_IN_REASONING=1
# GLM53_ADAPTIVE_K off (upstream default; measured negative on our workload)
# GLM53_DENSE_FP8 unset (upstream default; marked provisional)

LANGUAGE_MODEL_ONLY=0
SKIP_MM_PROFILING=1
LIMIT_MM='{"image":100,"video":1}'
CG_ESTIMATE=1
USE_HOST_NCCL=0
```

Boot receipt to expect: `GPU KV cache size: 1,020,958 tokens, Maximum concurrency
for 850,000 tokens per request: 1.20x` and `Available KV cache memory: 16.79 GiB`.

## Deltas for the 2026-09-18 thin-decode A/B

On top of the v1.5 block above:

```
GPU_MEM_UTIL=0.86                          # was 0.89; 0.89 OOM-killed the head's user session
EXTRA_ARGS="--kv-cache-memory-bytes 15569256448"   # 14.5 GiB KV pin
CG_ESTIMATE=0                              # return over-estimated CUDA-graph reservation to KV
LOAD_FORMAT=instanttensor                  # this image has the wheel; empty = slow auto loader
GLM53_EXL3_MOE_FAST=1                      # thin-decode; needs an image built from >= ca29e28
```

Both `docker run` lines in `start.sh` carry `--oom-score-adj 1000` locally so the
engine is killed before sshd/systemd if memory runs out. Pool: 915,507 tok / 1.08x.

## 2026-09-19: `GLM53_MIXED_PREFILL_CHUNK=fair`

Replaces `skip` in every block above. `skip` denies admission to any new request
while another is decoding, with no deferral cap; on a shared endpoint that is a
multi-minute freeze for one-line prompts. `fair` v5 (upstream default since
2026-09-15) gives a newcomer its first token in ~12-17 s while the incumbent keeps
streaming. Bind-mounted overlay, no rebuild; restart required.
