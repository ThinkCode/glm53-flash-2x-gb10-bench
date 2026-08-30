# Upstream pins — what these numbers were measured against

Both recipes were moving fast while we measured (Mia's repo took 20 commits in a
single day). Pin these to reproduce; a later `main` may not behave the same.

## EXL3 — MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks

```
79f10b91f84779b2b1ff2c9327b1a5847cd97f70   2026-08-29
Merge pull request #40 from MiaAI-Lab/feat/prefill-mnbt-2048
```

```bash
git clone https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks
cd GLM-5.3-Flash-EXL3-2x-DGX-Sparks
git checkout 79f10b91f84779b2b1ff2c9327b1a5847cd97f70
BUILD=1 ./start.sh restart      # local build; published image lagged this commit
```

This is the exact tree our serving image was built from — verified on the node, not
inferred. **Build locally.** The published GHCR image was a day behind its own
`main` when we checked, missing that day's XGrammar termination fixes and bring-up
robustness work. The build compiles the `exllamav3` wheel and takes ~25–30 minutes.

Notable in this pin: `MAX_NUM_BATCHED_TOKENS` moved 1024 → 2048 (commit `c9f731f`)
after upstream's cold-prefill ladder. We measured on 2048.

## NVFP4 — tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark

```
7497e96b8fb46ed837f51b58f0e15943c8cb9658   2026-08-29
docs: flag RedHatAI compressed-tensors as default checkpoint (fixes ModelOpt
token corruption, vLLM #54150)
```

```bash
git clone https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark
cd GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark
git checkout 7497e96b8fb46ed837f51b58f0e15943c8cb9658
```

**Be precise about what this pin is.** We did not build from a pinned local clone of
this repo the way we did for EXL3 — our launcher was assembled from the recipe and
has since diverged. This SHA is the commit whose *guidance* our configuration
matches, in particular the RedHatAI checkpoint default. Treat
[`nvfp4.md`](nvfp4.md) as the authoritative description of what we actually ran; use
this SHA to read the reasoning behind it.

Two earlier commits worth reading at this pin:

| commit | why |
|---|---|
| `53853387d9ec79e956807f1d5f15fc96d841173c` | withdraws upstream's own pinned-KV guidance as unsafe — read before copying any `--kv-cache-memory` value |
| `10f5ec007070e25743b101a5048f545fe31320b5` | `docs/OPEN-PROBLEMS.md`, the known failures |

Upstream `main` has moved past this pin (`1f03bab`, 2026-08-30, repointing images at
public GHCR). Their open issue **#12** proposes a 6 GiB KV pin, `k=5`, and
`--max-num-batched-tokens 8192` for +65 tok/s at C6. We tested the first two:
neither helped our workload — see the README. Their gain is real for a short-prompt
sweep where the KV pool is the binding constraint; at 100k with concurrent streams
it is not.

## Shared

| | |
|---|---|
| Drafter | `incoai/GLM-5.3-Flash-DFlash2` |
| NVFP4 weights | `RedHatAI/GLM-5.3-Flash-NVFP4` (compressed-tensors) |
| EXL3 weights | `Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw` |

HuggingFace repos are mutable. If you need byte-exact reproduction, pin the model
revisions too — `MODEL_REVISION` in the EXL3 env, and `--revision` for vLLM.
