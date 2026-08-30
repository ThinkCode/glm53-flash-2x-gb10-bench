#!/usr/bin/env python3
"""Phase A re-run for EXL3 with thinking OFF.

The first pass captured 0 chars: EXL3 defaults to thinking ON, so all 1024
tokens went to reasoning and no answer was emitted. NVFP4's launcher sets
enable_thinking false by default, so this makes the two comparable.
"""
import json, os, time, urllib.request

EP = "http://127.0.0.1:8600/v1/chat/completions"
MODEL = "glm-5.3-flash-exl3"
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

out = []
for wl, prompt in WORKLOADS.items():
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024, "temperature": 0, "stream": True,
            "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(EP, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    first = last = None; n = 0; text = []
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1200) as r:
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
            for ch in d.get("choices") or []:
                c = (ch.get("delta") or {}).get("content") or ""
                if c:
                    now = time.time()
                    if first is None: first = now
                    last = now
                    text.append(c)
    wall = time.time() - t0
    s = "".join(text)
    dec = (n - 1) / (last - first) if last and first and last > first else 0
    ttft = (first - t0) if first else 0
    with open("%s/%s__%s.md" % (OUTDIR, wl, MODEL), "w") as fh:
        fh.write("# %s / %s\n\n- decode %.1f tok/s\n- TTFT %.2fs\n- wall %.1fs\n"
                 "- %d tokens generated\n\n---\n\n%s\n" % (wl, MODEL, dec, ttft, wall, n, s))
    out.append({"workload": wl, "model": MODEL, "decode": dec, "ttft": ttft,
                "wall": wall, "gen_tokens": n, "chars": len(s)})
    print("  %-16s %5.1f tok/s  TTFT %.2fs  wall %5.1fs  %d tok  %d chars"
          % (wl, dec, ttft, wall, n, len(s)), flush=True)

json.dump(out, open("/tmp/glm53-phaseA-exl3.json", "w"), indent=1)
print("wrote /tmp/glm53-phaseA-exl3.json", flush=True)
