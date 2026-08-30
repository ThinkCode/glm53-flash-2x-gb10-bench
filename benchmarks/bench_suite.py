#!/usr/bin/env python3
"""Full GLM-5.3 A/B suite: real coding workloads, depth sweep, concurrency matrix.

Emits:
  /tmp/glm53-results.json   machine-readable, for charts
  /tmp/glm53-outputs/       the ACTUAL generated code for each workload

Every prompt carries a unique salt so the prefix cache cannot serve one run from
another's work -- otherwise TTFT is fiction.
"""
import json, os, statistics, sys, threading, time, urllib.request, uuid

EP = "http://127.0.0.1:8600/v1/chat/completions"
MODELS = ["glm-5.3-flash-nvfp4", "glm-5.3-flash-exl3"]
OUTDIR = "/tmp/glm53-outputs"
os.makedirs(OUTDIR, exist_ok=True)

WORKLOADS = {
    "ios-swift": "Write a complete SwiftUI login screen: email/password fields with "
                 "validation, an async/await login call, an ObservableObject view model, "
                 "loading and error states, and a preview. Production quality.",
    "android-kotlin": "Write a complete Android Jetpack Compose screen in Kotlin: a "
                      "paginated list from a Retrofit API, ViewModel with StateFlow, "
                      "Repository, loading/error/empty states, and Hilt injection.",
    "website": "Write a responsive product landing page: semantic HTML5, CSS grid with a "
               "mobile breakpoint, dark mode via prefers-color-scheme, and vanilla JS for "
               "a sticky nav plus a form that validates before submit. No frameworks.",
    "python": "Write a Python module: an async worker pool that rate-limits outbound HTTP "
              "calls, retries with exponential backoff and jitter, full type hints, "
              "docstrings, and pytest tests using respx.",
}

FILLER = '''
class Handler{i}:
    """Legacy ingestion handler {i}. Retained for the migration window."""
    RETRIES = {i}
    def __init__(self, session, shard={i}):
        self.session, self.shard = session, shard
        self._cache = {{}}
    def normalise(self, rec):
        key = rec["id_{i}"].strip().lower()
        amt = float(rec.get("amount_{i}", 0.0))
        if amt < 0:
            raise ValueError("negative amount for %s" % key)
        return {{"key": key, "amount": amt, "shard": self.shard}}
    def flush(self):
        out = list(self._cache.values()); self._cache.clear(); return out
'''


def ctx_prefix(target_tokens, salt):
    """~target_tokens of plausible repo context, unique per call."""
    if target_tokens <= 0:
        return ""
    body, i = [], 0
    while sum(len(x) for x in body) < target_tokens * 3.6:
        body.append(FILLER.format(i=i)); i += 1
    return ("// context salt=%s -- existing service code, for reference\n%s\n\n"
            % (salt, "".join(body)))


def call(model, prompt, max_tokens):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0, "stream": True,
            "stream_options": {"include_usage": True}}
    req = urllib.request.Request(EP, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    first = last = None
    n = ptok = 0
    text = []
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
                    dl = ch.get("delta") or {}
                    c = dl.get("content") or ""
                    r_ = dl.get("reasoning_content") or dl.get("reasoning") or ""
                    if c or r_:
                        now = time.time()
                        if first is None:
                            first = now
                        last = now
                        if c:
                            text.append(c)
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, str(e)[:80])}
    wall = time.time() - t0
    return {"ttft": (first - t0) if first else 0,
            "decode": (n - 1) / (last - first) if last and first and last > first else 0,
            "gen_tokens": n, "prompt_tokens": ptok, "wall": wall,
            "text": "".join(text)}


results = {"quality": [], "depth": [], "concurrency": []}

# ---- Phase A: real coding output, captured -------------------------------
print("=== PHASE A: coding workloads, 1024 tokens, output captured ===", flush=True)
for wl, prompt in WORKLOADS.items():
    for model in MODELS:
        r = call(model, prompt, 1024)
        if "error" in r:
            print("  %-16s %-22s FAILED %s" % (wl, model, r["error"]), flush=True)
            continue
        fn = "%s/%s__%s.md" % (OUTDIR, wl, model)
        with open(fn, "w") as fh:
            fh.write("# %s / %s\n\n- decode %.1f tok/s\n- TTFT %.2fs\n- wall %.1fs\n"
                     "- %d tokens generated\n\n---\n\n%s\n"
                     % (wl, model, r["decode"], r["ttft"], r["wall"], r["gen_tokens"], r["text"]))
        results["quality"].append({"workload": wl, "model": model, "decode": r["decode"],
                                   "ttft": r["ttft"], "wall": r["wall"],
                                   "gen_tokens": r["gen_tokens"], "chars": len(r["text"]),
                                   "file": fn})
        print("  %-16s %-22s %5.1f tok/s  TTFT %.2fs  wall %5.1fs  %d tok  %d chars"
              % (wl, model, r["decode"], r["ttft"], r["wall"], r["gen_tokens"], len(r["text"])), flush=True)

# ---- Phase B: depth sweep, single stream ---------------------------------
print("\n=== PHASE B: depth sweep, single stream, 256 tokens ===", flush=True)
for depth in [8000, 32000, 100000]:
    for model in MODELS:
        p = ctx_prefix(depth, uuid.uuid4().hex) + \
            "Given the code above, write a Python function that validates a batch of " \
            "records and returns (valid, errors). Include type hints and docstring."
        r = call(model, p, 256)
        if "error" in r:
            print("  %6dk %-22s FAILED %s" % (depth // 1000, model, r["error"]), flush=True)
            continue
        pf = r["prompt_tokens"] / r["ttft"] if r["ttft"] else 0
        results["depth"].append({"depth": depth, "model": model, "decode": r["decode"],
                                 "ttft": r["ttft"], "prompt_tokens": r["prompt_tokens"],
                                 "prefill_tok_s": pf, "wall": r["wall"]})
        print("  %5dk  %-22s prompt=%7d  TTFT %6.1fs (%5.0f tok/s prefill)  decode %5.1f tok/s"
              % (depth // 1000, model, r["prompt_tokens"], r["ttft"], pf, r["decode"]), flush=True)

# ---- Phase C: concurrency matrix -----------------------------------------
print("\n=== PHASE C: concurrency x depth ===", flush=True)
MATRIX = [(8000, [1, 2, 4, 6]), (32000, [1, 2, 3]), (100000, [1, 2, 3])]
for depth, levels in MATRIX:
    for model in MODELS:
        for n in levels:
            out = {}
            def worker(i):
                p = ctx_prefix(depth, uuid.uuid4().hex) + \
                    "Given the code above, write a Python function that validates a " \
                    "batch of records and returns (valid, errors). Type hints please."
                out[i] = call(model, p, 256)
            ths = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
            t0 = time.time()
            for t in ths: t.start()
            for t in ths: t.join()
            wall = time.time() - t0
            good = [v for v in out.values() if "error" not in v]
            if not good:
                print("  %5dk C%-2d %-22s ALL FAILED" % (depth // 1000, n, model), flush=True)
                continue
            per = statistics.median(v["decode"] for v in good)
            agg = sum(v["decode"] for v in good)
            ttft = statistics.median(v["ttft"] for v in good)
            results["concurrency"].append({"depth": depth, "model": model, "streams": n,
                                           "per_stream": per, "aggregate": agg,
                                           "ttft": ttft, "wall": wall,
                                           "errors": len(out) - len(good)})
            print("  %5dk C%-2d %-22s per-stream %5.1f  aggregate %6.1f  TTFT %6.1fs  wall %6.1fs"
                  % (depth // 1000, n, model, per, agg, ttft, wall), flush=True)

with open("/tmp/glm53-results.json", "w") as fh:
    json.dump(results, fh, indent=1)
print("\nwrote /tmp/glm53-results.json and %s/" % OUTDIR, flush=True)
