"""Ask the deployed copilot a question and print the answer plus the MCP tool-call trace.
Usage: python tools/ask_live.py "<question>" [base_url]"""
import json
import sys
import time
import urllib.request

q = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else "https://mazharrasyad.tech/kelurahan-copilot"
req = urllib.request.Request(f"{base}/api/ask", data=json.dumps({"question": q}).encode(), headers={"content-type": "application/json"})
t0 = time.time()
try:
    d = json.load(urllib.request.urlopen(req, timeout=180))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])
    sys.exit(1)
print(f"Q: {q}\n({time.time() - t0:.1f}s, {len(d['steps'])} tool calls, {d['model']})\n")
print(d["answer"])
print("\n--- trace")
for s in d["steps"]:
    print(f"  [{s['system']}] {s['tool']}({', '.join(f'{k}={v}' for k, v in s['args'].items())}) ok={s['ok']} -> {s['summary']} ({s['ms']} ms)")
