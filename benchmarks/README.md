# Benchmarks

| script | what it does |
|---|---|
| `bench_suite.py` | Full matrix — 4 coding workloads with output capture, single-stream depth sweep (8k/32k/100k), concurrency × depth. Writes `results.json`. |
| `bench_phase_a_thinking_off.py` | Re-runs the coding workloads with `enable_thinking: false`, required for any engine that defaults to thinking on. |

Point `EP` at your OpenAI-compatible endpoint and set `MODELS` to the ids it serves.

Decode rate is measured from **first token to last**, excluding prefill, so it is not
diluted by TTFT. Prefill rate is `prompt_tokens / TTFT`. Each prompt gets a UUID salt
so the prefix cache cannot serve it from a previous run.
