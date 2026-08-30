# NVFP4 + DFlash2 — key settings

Two GB10 nodes, tensor-parallel 2. Recipe:
[tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark](https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark).

## Weights

| | |
|---|---|
| Model | `RedHatAI/GLM-5.3-Flash-NVFP4` (**compressed-tensors**) |
| Drafter | `incoai/GLM-5.3-Flash-DFlash2` (2.2 GiB, bind-mounted read-only on both ranks) |

**Use the compressed-tensors build, not a ModelOpt one.** ModelOpt NVFP4 quants of
this model emit corrupted token ids
([vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)). We reproduced it
at temperature 0 with no tools and no streaming — a Korean probe scored a median of
3 `U+FFFD` per response on `LibertAIDAI/GLM-5.3-Flash-NVFP4` and **0** on the
RedHatAI build, one variable changed. It is nearly invisible in English, so it can
run for days unnoticed; when a corrupted token lands inside a tool-call block the
parser desyncs and generation can spiral.

Tradeoff: the compressed-tensors build is W4A4 (activations quantized too) where the
weight-only builds are W4A16, so expect slightly lower scores on hard reasoning.

## Engine flags

```
--tensor-parallel-size 2
--load-format instanttensor
--gpu-memory-utilization 0.85
--kv-cache-memory 4294967296          # 4 GiB pin -> 410,427-token pool, 1.57x at 262k
--max-model-len 262144
--max-num-seqs 6
--block-size 2304
--moe-backend marlin
--max-num-batched-tokens 1024
--kv-cache-dtype fp8_e4m3
--enforce-eager
--speculative-config '{"method":"dflash",
                       "model":"/models/glm-5.3-flash-dflash2",
                       "num_speculative_tokens":7,
                       "draft_tensor_parallel_size":1,
                       "kv_cache_dtype":"auto",
                       "draft_sample_method":"probabilistic",
                       "rejection_sample_method":"standard"}'
--tool-call-parser glm47 --enable-auto-tool-choice
--reasoning-parser glm45
--default-chat-template-kwargs '{"enable_thinking": false}'
--distributed-executor-backend mp --nnodes 2 --node-rank <0|1>
```

## Gotchas that cost us time

- **The drafter key is `model`, not `draft_model_name_or_path`.** Upstream's notes
  say the latter; vLLM's `SpeculativeConfig` rejects it and both ranks die at
  argument parsing before any weight loads.
- **`--gpu-memory-utilization` is a fraction of TOTAL, not of free.** vLLM refuses
  to boot unless free >= total x util. On a 121 GiB unified-memory box, 0.90 wants
  109.5 GiB and fails at 109.3 free.
- **Unified memory means the host shares the pool.** Pushing utilisation to 0.89
  booted and served for hours, then starved the head so hard that `sshd` could no
  longer fork — TCP accepted, banner exchange timed out, on every interface. It
  needed a physical power cycle. Leave headroom.
- **A pinned `--kv-cache-memory` makes vLLM skip the activation-peak subtraction.**
  It hands back exactly what you ask for, so `--gpu-memory-utilization` becomes
  dead and the pool has no headroom for a real forward pass. Upstream withdrew its
  own pinned-KV guidance for this reason. We keep the pin deliberately, for host
  headroom, having accepted that hazard.
- **Flush the page cache with the engine STOPPED before any pin change.** Stopping
  first frees the model's page cache; the new slab then allocates out of a clean
  ~120 GiB and the host ends up with *more* headroom, not less.
- **Raising the KV pool does not fix concurrent throughput.** See the README —
  4 -> 5 GiB (+25% pool) changed nothing, because nothing was ever being evicted.

## Prefix caching does not work on this stack

**Zero hits, ever** — 442,227 lookups, 0 hits. The engine enables prefix caching,
then disables the hit path:

```
WARNING [kv_cache_coordinator.py:611] Disabling fine-grained prefix-cache hits
because these KV cache managers require block-aligned lookups: KpoolTailManager
```

`KpoolTailManager` comes from the SM121 sparse-attention indexer patch (deviation 7)
that this recipe requires on GB10. There is no alignment workaround: a prompt
binary-searched to exactly 4608 tokens (2 × block-size 2304) and sent twice still
gets 0 hits, as does the unaligned control.

**If you are running multi-turn or agent workloads, this is the single most
important fact about this deployment.** Every turn re-prefills the whole
conversation — at 100k context and ~1000 tok/s prefill, roughly 100 s per turn of
pure re-computation. It is invisible on single-shot prompts, which is why it took us
a week of benchmarking to find.

Filed upstream as
[tonyd2wild#13](https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark/issues/13).
Check whether it is fixed before assuming any concurrency number here still applies.

## Fabric

Dual-rail RoCE, both NICs listed in `NCCL_IB_HCA`, with:

```
NCCL_IB_GID_INDEX=3      # pin it; auto-selection picks a link-local GID and hangs
NCCL_CROSS_NIC=1
NCCL_IB_MERGE_NICS=0
NCCL_NVLS_ENABLE=0
NCCL_CUMEM_ENABLE=0
NCCL_IGNORE_CPU_AFFINITY=1
TORCH_NCCL_ASYNC_ERROR_HANDLING=1
```

Verify GID 3 is the RoCEv2 IPv4 entry on both HCAs and both ranks before blaming
the fabric — a mismatched index looks exactly like a dead link.
