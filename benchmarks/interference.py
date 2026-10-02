#!/usr/bin/env python3
"""Does a newcomer disturb a stream that is already decoding?  usage: interference.py BASE MODEL
 A) incumbent = long answer (thinking off, 1500 tok). After 8 s a SHORT newcomer arrives -> newcomer TTFT, incumbent rate before/after.
 B) incumbent as above. After 8 s a COLD ~32k-token prompt arrives -> its TTFT, and the incumbent's worst 2-second decode rate while it prefills."""
import json, random, statistics as st, sys, threading, time, urllib.request, uuid
BASE, MODEL = sys.argv[1], sys.argv[2]
def post(path, body, timeout=900):
    return json.loads(urllib.request.urlopen(urllib.request.Request(BASE+path, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}), timeout=timeout).read())
W=("alpha beta gamma delta kernel tensor matrix vector latency throughput memory cache stream decode prefill token batch queue socket packet fabric "
   "switch cluster node rank shard expert router gate layer attention hidden state buffer window context prompt answer model weight bias scale norm").split()
def text(target):
    r=random.Random(7); body=lambda n:" ".join(r.choice(W) for _ in range(n))
    n=int(target/1.3)
    for _ in range(3):
        t=f"[nonce {uuid.uuid4().hex[:10]}] "+body(n); c=post("/tokenize",{"prompt":t})["count"]
        if abs(c-target)<0.02*target: return t
        n=int(n*target/c)
    return t
def stream(msgs, max_tokens, marks):
    body={"model":MODEL,"messages":msgs,"max_tokens":max_tokens,"temperature":0,"stream":True,"stream_options":{"include_usage":True},"chat_template_kwargs":{"enable_thinking":False}}
    req=urllib.request.Request(BASE+"/v1/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    t0=time.perf_counter(); marks["t0"]=t0; ts=[]
    with urllib.request.urlopen(req,timeout=900) as r:
        for line in r:
            line=line.decode().strip()
            if not line.startswith("data:") or line=="data: [DONE]": continue
            d=json.loads(line[5:])
            for ch in d.get("choices") or []:
                dl=ch.get("delta") or {}
                if dl.get("content") or dl.get("reasoning_content"): ts.append(time.perf_counter())
    marks["ts"]=ts; marks["t_end"]=time.perf_counter()
def rate(ts,a,b):
    n=sum(1 for t in ts if a<=t<b); return n/(b-a) if b>a else 0
def scenario(label, newcomer_msgs, newcomer_max):
    inc={}; new={}
    ti=threading.Thread(target=stream,args=([{"role":"user","content":"Write a long, detailed essay about the history of the Silk Road, with many sections."}],1500,inc)); ti.start()
    time.sleep(8.0); tn_start=time.perf_counter()
    tn=threading.Thread(target=stream,args=(newcomer_msgs,newcomer_max,new)); tn.start(); tn.join(); tn_end=new["t_end"]
    ti.join(); ts=inc["ts"]
    ttft=(new["ts"][0]-new["t0"]) if new["ts"] else None
    before=rate(ts,tn_start-6,tn_start)                        # steady rate in the 6 s before the newcomer
    during=rate(ts,tn_start,tn_end) if tn_end>tn_start else 0   # rate while the newcomer was in flight
    worst=min((rate(ts,a,a+2) for a in [tn_start+i*0.5 for i in range(int(max(0,(tn_end-tn_start-2))/0.5)+1)]), default=0)
    gaps=[b-a for a,b in zip(ts,ts[1:]) if tn_start<=a<=tn_end]
    out={"scenario":label,"newcomer_ttft_s":round(ttft,2) if ttft else None,"newcomer_total_s":round(tn_end-tn_start,2),
         "incumbent_rate_before":round(before,1),"incumbent_rate_during":round(during,1),"incumbent_worst_2s_window":round(worst,1),
         "incumbent_longest_gap_s":round(max(gaps),2) if gaps else None,"incumbent_kept_pct":round(100*during/before,0) if before else None}
    print(json.dumps(out),flush=True); return out
res=[]
res.append(scenario("A: short newcomer ('What is 17*23?')",[{"role":"user","content":"What is 17 times 23? Answer with just the number."}],16))
res.append(scenario("B: cold ~32k-token newcomer",[{"role":"user","content":text(32000)+"\n\nReply with just: OK"}],8))
json.dump(res,open(f"/tmp/tfbench/interference_{MODEL}.json","w"),indent=1)
