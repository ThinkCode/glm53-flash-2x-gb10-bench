#!/usr/bin/env python3
"""Fire N streams at EACH of two endpoints at the same instant; report per-stream decode rate and the combined
aggregate = total completion tokens / wall time of the whole wave (the honest metric; never a sum of per-stream rates).
usage: both_wave.py N runs     (structured prompt, 400 tokens, temp 0, thinking off — same protocol as bench_decode.py)"""
import json, statistics as st, sys, threading, time, urllib.request
EPS = [("http://HEAD1:8888", "glm-5.3-flash-1"), ("http://HEAD2:8888", "glm-5.3-flash-2")]
N = int(sys.argv[1]); RUNS = int(sys.argv[2])
PROMPT = "Count from 1 to 200. Output only the numbers, separated by spaces. No other text."
def one(ep, model, res, i):
    ei, k = i
    body = {"model": model, "messages": [{"role": "user", "content": f"{PROMPT} (stream {k+1}/{N})" if N > 1 else PROMPT}], "max_tokens": 400, "temperature": 0, "top_p": 1,
            "stream": True, "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False, "thinking": False, "thinking_mode": "disabled"},
            "min_tokens": 400, "ignore_eos": True, "stop": []}
    req = urllib.request.Request(ep + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); first = last = None; toks = 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            d = json.loads(line[5:])
            if d.get("usage"): toks = d["usage"]["completion_tokens"]
            for ch in d.get("choices") or []:
                dl = ch.get("delta") or {}
                if dl.get("content") or dl.get("reasoning_content"):
                    now = time.time(); first = first or now; last = now
    res[i] = {"model": model, "tokens": toks, "tf": first, "tl": last, "ttft": (first - t0) if first else None,
              "rate": (toks - 1) / (last - first) if first and last and last > first and toks > 1 else None}
def wave():
    res = {}; ths = []
    for ei, (ep, m) in enumerate(EPS):
        for k in range(N):
            t = threading.Thread(target=one, args=(ep, m, res, (ei, k))); ths.append(t)
    t0 = time.time()
    for t in ths: t.start()
    for t in ths: t.join()
    wall = time.time() - t0
    return res, wall
wave()  # warmup (shapes)
out = []
for r in range(RUNS):
    res, wall = wave(); tot = sum(v["tokens"] for v in res.values())
    rates = [v["rate"] for v in res.values() if v["rate"]]
    per = {m: round(st.median([v["rate"] for v in res.values() if v["model"] == m and v["rate"]]), 1) for _, m in EPS}
    win = max(v["tl"] for v in res.values()) - min(v["tf"] for v in res.values()); dec = sum(v["tokens"] - 1 for v in res.values())
    rec = {"run": r + 1, "streams_total": 2 * N, "aggregate_tok_s": round(tot / wall, 1), "aggregate_decode_window_tok_s": round(dec / win, 1), "per_stream_median": round(st.median(rates), 1),
           "per_instance_median": per, "ttft_median_s": round(st.median([v["ttft"] for v in res.values() if v["ttft"]]), 3), "wall_s": round(wall, 2)}
    out.append(rec); print(json.dumps(rec), flush=True)
agg = [o["aggregate_decode_window_tok_s"] for o in out]
print(json.dumps({"summary": f"2 x {N} streams", "aggregate_decode_window_tok_s_median": round(st.median(agg), 1), "aggregate_wall_tok_s_median": round(st.median(o["aggregate_tok_s"] for o in out), 1), "min": min(agg), "max": max(agg),
                  "sd": round(st.pstdev(agg), 1), "per_stream_median": round(st.median([o["per_stream_median"] for o in out]), 1)}))
json.dump(out, open(f"/tmp/tfbench/both_x{N}.json", "w"), indent=1)
