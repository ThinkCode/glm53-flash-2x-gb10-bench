#!/usr/bin/env python3
"""Faithful Python port of sparkDash's DecodeBench wave (MiaAI-Lab/sparkDash @ b4228a3, server/collectors/DecodeBench.js):
 - prompts: structured/prose share one prompt but concurrent streams get a unique ' (stream i/n)' suffix; code = one distinct task per stream
 - body: temperature 0, top_p 1, stream + include_usage, chat_template_kwargs {enable_thinking,thinking: false, thinking_mode: disabled},
         min_tokens = max_tokens, ignore_eos true, stop []
 - per-stream decodeTps = (completion_tokens - 1) / (lastToken - firstToken); ttft = firstToken - requestStart
 - aggregate = sum(decodeTokens) / (max(lastToken) - min(firstToken))   [decode window only, no prefill]
 - warmup: one 32-token stream first.   usage: sparkdash_decode.py BASE MODEL TYPE CONCS REPS OUTDIR"""
import json, statistics as st, sys, threading, time, urllib.request, os
BASE, MODEL, TYPE = sys.argv[1], sys.argv[2], sys.argv[3]
CONCS = [int(x) for x in sys.argv[4].split(",")]; REPS = int(sys.argv[5]); OUT = sys.argv[6]; os.makedirs(OUT, exist_ok=True)
P = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sparkdash_prompts.json")))
MAX = 400
def prompts(n):
    if TYPE == "code": return [P["code_tasks"][i % len(P["code_tasks"])] if i < len(P["code_tasks"]) else f"[stream {i+1}]\n"+P["code_tasks"][i % len(P["code_tasks"])] for i in range(n)]
    base = P[TYPE]
    return [base] if n <= 1 else [f"{base} (stream {i+1}/{n})" for i in range(n)]
def body(prompt, max_tokens, force):
    b = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0, "top_p": 1,
         "stream": True, "stream_options": {"include_usage": True},
         "chat_template_kwargs": {"enable_thinking": False, "thinking": False, "thinking_mode": "disabled"}}
    if force: b.update({"min_tokens": max_tokens, "ignore_eos": True, "stop": []})
    return b
def stream(prompt, max_tokens, force, res, i):
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body(prompt, max_tokens, force)).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter(); tf = tl = None; toks = 0; chunks = 0; err = None
    try:
        with urllib.request.urlopen(req, timeout=360) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data:") or line == "data: [DONE]": continue
                d = json.loads(line[5:])
                if d.get("usage"): toks = int(d["usage"].get("completion_tokens") or 0)
                for ch in d.get("choices") or []:
                    dl = ch.get("delta") or {}
                    if dl.get("content") or dl.get("reasoning_content") or dl.get("reasoning"):
                        now = time.perf_counter(); chunks += 1
                        if tf is None: tf = now
                        tl = now
    except Exception as e: err = str(e)[:120]
    toks = toks or chunks
    dt = max(0, toks - 1)
    res[i] = {"t0": t0, "tf": tf, "tl": tl, "toks": toks, "dtoks": dt, "err": err,
              "ttft_ms": (tf - t0) * 1000 if tf else None, "tps": (dt / (tl - tf)) if tf and tl and tl > tf and dt > 0 else 0}
def wave(c):
    res = {}; ps = prompts(c); ths = [threading.Thread(target=stream, args=(ps[i], MAX, True, res, i)) for i in range(c)]
    w0 = time.perf_counter()
    for t in ths: t.start()
    for t in ths: t.join()
    ok = [r for r in res.values() if not r["err"] and r["dtoks"] > 0]
    if not ok: return {"concurrency": c, "error": [r["err"] for r in res.values()][:2]}
    win = max(r["tl"] for r in ok) - min(r["tf"] for r in ok)
    return {"concurrency": c, "streams_ok": len(ok), "median_tps": round(st.median(r["tps"] for r in ok), 2), "mean_tps": round(st.mean(r["tps"] for r in ok), 2),
            "min_tps": round(min(r["tps"] for r in ok), 2), "max_tps": round(max(r["tps"] for r in ok), 2),
            "aggregate_tps": round(sum(r["dtoks"] for r in ok) / win, 2) if win > 0 else 0, "ttft_median_ms": round(st.median(r["ttft_ms"] for r in ok), 1),
            "wave_s": round(time.perf_counter() - w0, 2)}
w = {}; stream(prompts(1)[0] if TYPE != "code" else P["code_tasks"][0], 32, False, w, 0)   # warmup (32 tokens), like the dashboard
summary = []
for c in CONCS:
    waves = [wave(c) for _ in range(REPS)]
    good = [x for x in waves if "error" not in x]
    if not good: print(json.dumps({"type": TYPE, "c": c, "error": waves[0]})); continue
    s = {"type": TYPE, "model": MODEL, "concurrency": c, "reps": len(good),
         "aggregate_tps_median": round(st.median(x["aggregate_tps"] for x in good), 1), "aggregate_range": [min(x["aggregate_tps"] for x in good), max(x["aggregate_tps"] for x in good)],
         "per_stream_median_tps": round(st.median(x["median_tps"] for x in good), 1), "per_stream_mean_tps": round(st.median(x["mean_tps"] for x in good), 1),
         "ttft_median_ms": round(st.median(x["ttft_median_ms"] for x in good)), "waves": waves}
    summary.append(s); json.dump(s, open(f"{OUT}/{TYPE}-x{c}.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in s.items() if k != "waves"}), flush=True)
