"""Thin wrapper around the opa CLI."""
import json, subprocess, tempfile, os
from concurrent.futures import ThreadPoolExecutor

ENTRY = "data.acme.wealth.result"

def check(rego):
    p = subprocess.run(["opa", "check", rego], capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or p.stdout).strip()

def _one(args):
    rego, inp = args
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(inp, f); path = f.name
    try:
        p = subprocess.run(["opa", "eval", "-f", "json", "-d", rego, "-i", path, ENTRY], capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return {"error": p.stderr.strip()[:300]}
        j = json.loads(p.stdout)
        if "result" not in j:
            return {"decision": "UNDEFINED", "missing_approvals": []}
        return j["result"][0]["expressions"][0]["value"]
    finally:
        os.unlink(path)

def evaluate(rego, inputs, workers=8):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(_one, [(rego, i) for i in inputs]))
