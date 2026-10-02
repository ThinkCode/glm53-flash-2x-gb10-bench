#!/usr/bin/env python3
"""Cold-prefill ladder + prompt-reuse probe against an OpenAI-compatible endpoint (TensorFold /tokenize for sizing).
usage: prefill_ladder.py BASE MODEL sizes_csv [reuse]   e.g. prefill_ladder.py http://h:8888 glm-5.3-flash-1 8192,16384 reuse
Cold = a unique nonce at the very start of every prompt, so no kept prompt state can match. Thinking off, max_tokens 8.
prefill tok/s = usage.prompt_tokens / time-to-first-token."""
import json, random, sys, time, urllib.request, uuid
BASE, MODEL = sys.argv[1], sys.argv[2]
SIZES = [int(x) for x in sys.argv[3].split(",")]
REUSE = len(sys.argv) > 4 and sys.argv[4] == "reuse"
rnd = random.Random(1234)
WORDS = ("alpha beta gamma delta kernel tensor matrix vector latency throughput memory cache stream decode prefill token "
         "batch queue socket packet fabric switch cluster node rank shard expert router gate layer attention hidden state "
         "buffer window context prompt answer model weight bias scale norm rotary index pool block page graph launch warp "
         "thread grid register shared global bandwidth clock power thermal fan rack cable port link lane rail host guest").split()
def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
def count(text):
    try: return post("/tokenize", {"prompt": text})["count"]
    except Exception: return None
def make_text(target_tokens, nonce):
    # calibrate tokens/word on a 4000-word sample, then size and refine once
    def words(n): return " ".join(rnd.choice(WORDS) for _ in range(n))
    sample = words(4000); c = count(sample) or 4000 * 1.3; tpw = c / 4000
    n = int(target_tokens / tpw)
    for _ in range(3):
        body = f"[nonce {nonce}] " + words(n)
        c = count(body)
        if c is None or abs(c - target_tokens) < 0.01 * target_tokens: return body
        n = int(n * target_tokens / c)
    return body
def timed(text, label):
    body = {"model": MODEL, "messages": [{"role": "user", "content": text + "\n\nReply with just: OK"}], "max_tokens": 8, "temperature": 0,
            "stream": True, "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); first = None; usage = None
    with urllib.request.urlopen(req, timeout=1800) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            d = json.loads(line[5:])
            if d.get("usage"): usage = d["usage"]
            for ch in d.get("choices") or []:
                dl = ch.get("delta") or {}
                if first is None and (dl.get("content") or dl.get("reasoning_content")): first = time.time() - t0
    total = time.time() - t0; pt = (usage or {}).get("prompt_tokens")
    return {"label": label, "prompt_tokens": pt, "ttft_s": round(first, 3) if first else None, "total_s": round(total, 3),
            "prefill_tok_s": round(pt / first, 1) if pt and first else None, "cached_tokens": ((usage or {}).get("prompt_tokens_details") or {}).get("cached_tokens")}
out = []
for size in SIZES:
    nonce = uuid.uuid4().hex[:12]; text = make_text(size, nonce)
    r = timed(text, f"cold {size}"); out.append(r); print(json.dumps(r), flush=True)
    if REUSE and size in (32768, 65536):
        r2 = timed(text, f"identical resend {size}"); out.append(r2); print(json.dumps(r2), flush=True)
if REUSE:   # shared long system prompt, different user message each time
    nonce = uuid.uuid4().hex[:12]; sysp = make_text(7900, nonce)
    def with_user(u):
        body = {"model": MODEL, "messages": [{"role": "system", "content": sysp}, {"role": "user", "content": u}], "max_tokens": 8, "temperature": 0,
                "stream": True, "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        t0 = time.time(); first = None; usage = None
        with urllib.request.urlopen(req, timeout=900) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data:") or line == "data: [DONE]": continue
                d = json.loads(line[5:])
                if d.get("usage"): usage = d["usage"]
                for ch in d.get("choices") or []:
                    dl = ch.get("delta") or {}
                    if first is None and (dl.get("content") or dl.get("reasoning_content")): first = time.time() - t0
        return {"label": f"shared 7.9k system prompt, user: {u[:20]}", "prompt_tokens": (usage or {}).get("prompt_tokens"), "ttft_s": round(first, 3) if first else None}
    for u in ("What is 2+2?", "Name a prime number.", "Say hello in French."):
        r = with_user(u); out.append(r); print(json.dumps(r), flush=True)
json.dump(out, open("/tmp/tfbench/prefill_result_%s.json" % MODEL, "w"), indent=1)
