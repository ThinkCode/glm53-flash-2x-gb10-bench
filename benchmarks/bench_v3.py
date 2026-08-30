#!/usr/bin/env python3
"""Concurrency benchmark v3 -- v2 plus forced-equal output length.

V2 FLAW THIS FIXES: nearly every request finished on "stop", not "length", so
each model chose its own output length -- EXL3 wrote ~110 tokens where NVFP4
wrote ~205. tokens/wall then partly measures verbosity, not speed. v3 sets
ignore_eos + min_tokens so every request emits exactly GEN tokens.

RUNS: set RUNS>1; each cell is repeated and the MEDIAN of each metric reported,
because v2 showed cell-to-cell variance large enough to flip conclusions.

Original v2 header follows.

Concurrency benchmark v2 -- rebuilt after a correct critique of v1.

WHAT V1 GOT WRONG (all confirmed in its own source):
  * "aggregate" was sum(per-stream decode rate). Those windows do not overlap,
    so it is not cluster throughput. True batch throughput is
    sum(completion_tokens) / batch_wall.
  * v1 stored no completion_tokens for concurrency rows, so nothing could be
    recomputed from the published artifact.
  * thinking was ON for EXL3 and OFF for NVFP4 in the whole concurrency phase.
  * the two engines ran different max_num_seqs (EXL3 4, NVFP4 6), so admission
    limits differed in every cell.
  * unique salt per stream defeated prefix caching by design -- a cold-prefill
    worst case presented as a typical agent workload.

WHAT THIS RECORDS PER REQUEST
  completion_tokens, prompt_tokens, t_first, t_last, wall, finish_reason.
  Everything downstream is derived, so any reader can recompute.

METRICS REPORTED
  batch_throughput  = sum(completion_tokens) / batch_wall     <- cluster
  decode_throughput = sum(completion_tokens) / decode_span    <- excludes prefill
  p50_latency       = median end-to-end per request           <- user
  p50_decode_rate   = median per-stream rate after first token
Both arms: COLD (unique salt) and WARM (shared prefix, cache reuse allowed).
"""
import json, os, statistics, sys, threading, time, urllib.request, uuid

EP = os.environ.get("EP", "http://127.0.0.1:8600/v1/chat/completions")
MODELS = ["glm-5.3-flash-nvfp4", "glm-5.3-flash-exl3"]
DEPTH = int(os.environ.get("DEPTH", "8000"))
LEVELS = [int(x) for x in os.environ.get("LEVELS", "1,2,4").split(",")]
GEN = int(os.environ.get("GEN", "256"))
OUT = os.environ.get("OUT", "/tmp/bench-v3.json")
RUNS = int(os.environ.get("RUNS", "3"))

FUNC = '''
def handler_{i}(records, *, retries={i}):
    out, failed = [], []
    for rec in records:
        try:
            key = rec["id_{i}"].strip().lower()
            val = float(rec.get("amount_{i}", 0.0))
            if val < 0: raise ValueError("negative " + key)
            out.append({{"key": key, "value": val}})
        except (KeyError, ValueError) as exc:
            failed.append((rec, str(exc)))
    return out, failed
'''

_SHARED = None
def shared_body():
    global _SHARED
    if _SHARED is None:
        b, i = [], 0
        while sum(len(x) for x in b) < DEPTH * 3.6:
            b.append(FUNC.format(i=i)); i += 1
        _SHARED = "".join(b)
    return _SHARED


def make_prompt(warm, stream_idx):
    body = shared_body()
    if warm:
        # identical prefix across streams; only the trailing question differs,
        # so the engine may legitimately reuse cached blocks.
        return ("// shared service module\n%s\n\nQuestion %d: name the three most "
                "serious bugs above. Be brief." % (body, stream_idx))
    return ("// salt=%s\n%s\n\nName the three most serious bugs above. Be brief."
            % (uuid.uuid4().hex, body))


def call(model, warm, idx, out):
    b = {"model": model,
         "messages": [{"role": "user", "content": make_prompt(warm, idx)}],
         "max_tokens": GEN, "temperature": 0, "stream": True,
         "stream_options": {"include_usage": True},
         "chat_template_kwargs": {"enable_thinking": False},
         "ignore_eos": True,  # v3: force exactly GEN tokens so output LENGTH stops
         "min_tokens": GEN}   # being a hidden variable in every throughput number
    req = urllib.request.Request(EP, data=json.dumps(b).encode(),
                                 headers={"Content-Type": "application/json"})
    first = last = None
    n = ptok = 0
    finish = None
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data: "):
                    continue
                p = line[6:]
                if p == "[DONE]":
                    break
                d = json.loads(p)
                if d.get("usage"):
                    n = d["usage"]["completion_tokens"]
                    ptok = d["usage"].get("prompt_tokens", 0)
                for ch in d.get("choices") or []:
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
                    dl = ch.get("delta") or {}
                    if dl.get("content") or dl.get("reasoning_content") or dl.get("reasoning"):
                        now = time.time()
                        if first is None:
                            first = now
                        last = now
    except Exception as e:
        out[idx] = {"error": "%s: %s" % (type(e).__name__, str(e)[:80])}
        return
    out[idx] = {"completion_tokens": n, "prompt_tokens": ptok,
                "t_start": t0, "t_first": first, "t_last": last,
                "ttft": (first - t0) if first else None,
                "wall": time.time() - t0, "finish_reason": finish}


results = []
print("bench v3  depth=%d  levels=%s  gen=%d (ignore_eos, forced)  runs=%d  thinking=off both" % (DEPTH, LEVELS, GEN, RUNS), flush=True)
for warm in (False, True):
    arm = "WARM" if warm else "COLD"
    print("\n=== %s prefix ===" % arm, flush=True)
    for model in MODELS:
        for n in LEVELS:
            reps = []
            for _rep in range(RUNS):
                out = {}
                ths = [threading.Thread(target=call, args=(model, warm, i, out)) for i in range(n)]
                t0 = time.time()
                for t in ths: t.start()
                for t in ths: t.join()
                batch_wall = time.time() - t0
                good = [v for v in out.values() if "error" not in v]
                errs = [v for v in out.values() if "error" in v]
                if not good:
                    continue
                tot = sum(v["completion_tokens"] for v in good)
                span = max(v["t_last"] for v in good) - min(v["t_first"] for v in good)
                reps.append({"batch_wall": batch_wall, "total_completion_tokens": tot,
                             "batch_throughput": tot / batch_wall,
                             "decode_throughput": (tot / span) if span > 0 else 0,
                             "p50_latency": statistics.median(v["wall"] for v in good),
                             "p50_decode_rate": statistics.median(
                                 (v["completion_tokens"] - 1) / (v["t_last"] - v["t_first"])
                                 for v in good if v["t_last"] > v["t_first"]),
                             "p50_ttft": statistics.median(v["ttft"] for v in good if v["ttft"]),
                             "errors": len(errs), "requests": good})
            if not reps:
                print("  %-4s %-22s C%-2d ALL FAILED" % (arm, model, n), flush=True)
                continue
            med = lambda k: statistics.median(r[k] for r in reps)
            results.append({"arm": arm, "model": model, "streams": n, "depth": DEPTH,
                            "runs": len(reps),
                            "batch_throughput": med("batch_throughput"),
                            "decode_throughput": med("decode_throughput"),
                            "p50_latency": med("p50_latency"),
                            "p50_decode_rate": med("p50_decode_rate"),
                            "p50_ttft": med("p50_ttft"),
                            "batch_wall": med("batch_wall"),
                            "total_completion_tokens": med("total_completion_tokens"),
                            "errors": sum(r["errors"] for r in reps),
                            "reps": reps})
            spread = max(r["batch_throughput"] for r in reps) - min(r["batch_throughput"] for r in reps)
            print("  %-4s %-22s C%-2d  batch %6.1f tok/s (spread %4.1f) | decode %6.1f | "
                  "p50 lat %6.1fs | p50 rate %5.1f | ttft %5.1fs | %d tok"
                  % (arm, model, n, med("batch_throughput"), spread, med("decode_throughput"),
                     med("p50_latency"), med("p50_decode_rate"), med("p50_ttft"),
                     med("total_completion_tokens")), flush=True)

json.dump(results, open(OUT, "w"), indent=1)
print("\nwrote %s" % OUT, flush=True)
