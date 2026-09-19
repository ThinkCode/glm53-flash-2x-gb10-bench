# GLM53_EXL3_MOE_FAST A/B — 2026-09-18

Recipe `ca85576`, local `BUILD=1` image (`glm53_fast_moe_version()=1`), same image
and same boot geometry in every arm. `tests/bench_decode.py`, 400 tok, temp 0,
thinking off, direct `:8888`.

| dir | env | runs | note |
|---|---|---|---|
| `A/` | `GLM53_EXL3_MOE_FAST=0` | 5 | stock arm |
| `B/` | `GLM53_EXL3_MOE_FAST=1` | 5 | first pass after a fresh boot — **discarded** from the headline, kept for provenance; same bimodal shape as B2 |
| `B2/` | `GLM53_EXL3_MOE_FAST=1` | 8 | warm; request counters bracketed it (47 served = 47 issued) |

Per-run tok/s are under `runs[].tok_s` in each JSON. Upstream issue: MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks#227.
