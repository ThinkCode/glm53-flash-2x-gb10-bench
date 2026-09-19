# Upstream pins — what these numbers were measured against

Both recipes were moving fast while we measured (Mia's repo took 20 commits in a
single day). Pin these to reproduce; a later `main` may not behave the same.

## EXL3 — MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks

```
b5ab809   2026-08-30
Merge pull request #26 from im0xMagnus/feat/per-rank-gid
```

Adds, over the earlier `79f10b9` pin: `DFLASH_DRAFT_TP=2` as the new default
(worth +37% per-stream at C4 here — see the README), a K-pool tail slot-mapping
fix that could **crash or silently corrupt the indexer on long generations**, and
per-rank GID handling. Take the kpool fix regardless of the throughput change;
that class of bug is invisible until it isn't.

Earlier pin, if you want the pre-`draft_tp` numbers:
`79f10b91f84779b2b1ff2c9327b1a5847cd97f70` (2026-08-29).

```bash
git clone https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks
cd GLM-5.3-Flash-EXL3-2x-DGX-Sparks
git checkout b5ab809
BUILD=1 ./start.sh restart      # local build; published image lagged this commit
```

This is the exact tree our serving image was built from — verified on the node, not
inferred. **Build locally.** The published GHCR image was a day behind its own
`main` when we checked, missing that day's XGrammar termination fixes and bring-up
robustness work. The build compiles the `exllamav3` wheel and takes ~25–30 minutes.

Notable in this pin: `MAX_NUM_BATCHED_TOKENS` moved 1024 → 2048 (commit `c9f731f`)
after upstream's cold-prefill ladder. We measured on 2048.

## EXL3 — v1.6 pin (2026-09-18)

```
ca85576   2026-09-18
Merge pull request #219 from MiaAI-Lab/fix/numerical-panel-evidence
```

| | |
|---|---|
| Image | **local `BUILD=1`** from this tree; recipe stamp `a58dae380c93…`; `exllamav3_ext.glm53_fast_moe_version() == 1`. The GHCR `:exl3-instanttensor` tag (`ef9f5013…`, 09-16) does **not** carry the thin-decode patch as of this date |
| Weights / drafter | unchanged from v1.5 (`25a44fd` / `dc77ff1c`) |

```bash
git checkout ca85576
BUILD=1 ./start.sh restart          # ~25-30 min; ships the image to the worker
# every later restart, until a rebuilt tag is published:
SKIP_PULL=1 ./start.sh restart
```

Thin-decode is opt-in: `GLM53_EXL3_MOE_FAST=1` in `.env`. It is fail-closed — on an
image without the patch it raises at weight load rather than degrading. See the
README's 2026-09-18 update for what it does to the run distribution.

## EXL3 — v1.5 pin (2026-09-17)

The 2026-09-17 reproduction above ran on a much newer tree. Everything below was
read off the live node, not inferred.

```
bc68f310f8d5e941227ce5c93e95bca43b50fd6c   2026-09-16
Merge pull request #202 from MiaAI-Lab/feat/cooperative-moe-c1
```

| | |
|---|---|
| Image | `ghcr.io/miaai-lab/glm-5.3-flash-2x-dgx-sparks:exl3-instanttensor`, config digest `sha256:ef9f5013c41adf93a5171abb809283be0f202b88fd14098e4434337715614c62` |
| Weights | `Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw` @ `25a44fdbf16862a46b7cc9921142c6c81350af2f` |
| Drafter | `incoai/GLM-5.3-Flash-DFlash2` @ `dc77ff1c99eeb2df044ee3d4f0094eb033fee410` |

```bash
git clone https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks
cd GLM-5.3-Flash-EXL3-2x-DGX-Sparks
git checkout bc68f31
cp .env.example .env            # then set HEAD_IP / WORKER_IP / CX7 pins for your kit
./start.sh                      # pulls the GHCR image; no local build needed at this pin
```

Unlike the `b5ab809` pin, the published image was **current with `main`** when we
checked (identical config digest), so a plain pull is enough. `main` was 3 commits
ahead (`6961fa0`): a TP3/TP4 launcher fix and the 1.5.0 CHANGELOG — nothing that
touches the 2-node path.

Two things moved upstream since the earlier pin that you should know before you
copy old env files:

- `MAX_MODEL_LEN` default is now **850000**, not 1M. `MAX_NUM_BATCHED_TOKENS=7168`
  together with `GLM53_INDEXER_WORKSPACE=rightsize` did **not** boot for us at 1M
  (the rightsize workspace is sized from MNBT, so the two compete for the same
  memory). At 850k it boots and gives a 1,020,958-token pool (1.20x).
- `GLM53_MIXED_PREFILL_CHUNK` now defaults to **`fair`** (v5, 2026-09-15). We still
  run `skip`. Not measured either way here; it is an interactivity feature.

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
