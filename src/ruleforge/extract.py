"""Policy sections + input contract -> candidate Rego + list of doubts. The extractor never sees the key."""
import argparse, json, os, re, time
from . import llm, opa

SYSTEM = """You turn a bank policy into executable Open Policy Agent (OPA) Rego, v1 syntax.
Rules:
- Only the policy text is the source of truth. Do not invent thresholds or roles.
- Use exactly the package, entrypoint, input field names, actions and role names from the contract.
- Output shape of data.acme.wealth.result: decision, required_approvals, missing_approvals, findings, executable.
- Decision precedence: DENY > HOLD > REQUIRE_APPROVAL > ALLOW. Fail closed: when a needed fact is missing or unverified, HOLD.
- Tag every rule with its policy rule ID (for example "M-02") in required_approvals and findings.
- Never treat a requester supplied value as a trusted fact beyond what the contract says.
- If the policy is ambiguous or two rules conflict, choose the stricter reading AND report it in doubts.
Rego v1 syntax is mandatory. Start with `import rego.v1`. Every rule body needs `if`, sets use `contains`, membership uses `in`.
Do not use the old style `allow { ... }` and do not use `default` as a variable name. Example:
```
package acme.wealth
import rego.v1
findings contains {"rule_id": "G-01", "kind": "hold", "detail": "..."} if { input.action == "x"; not input.ok }
decision := "DENY" if { some f in findings; f.kind == "deny" }
else := "ALLOW"
```
Reply with exactly two fenced blocks: ```rego ...``` with the full file, then ```json ...``` with a list of
{"rule_id": str, "kind": "ambiguity"|"conflict"|"assumption", "note": str}."""

def build_prompt(sections, contract):
    body = "\n\n".join(f"[{s['id']}] {s['title']}\n{s['text']}" for s in sections)
    return f"INPUT CONTRACT (json):\n{json.dumps(contract, indent=1)}\n\nPOLICY TEXT:\n{body}"

def parse(text):
    rego = re.search(r"```rego\s*(.*?)```", text, re.S)
    js = re.search(r"```json\s*(.*?)```", text, re.S)
    doubts = []
    if js:
        try: doubts = json.loads(js.group(1))
        except Exception: pass
    return (rego.group(1).strip() + "\n" if rego else ""), doubts

def run_once(model, sections, contract, out_dir, repair=1):
    os.makedirs(out_dir, exist_ok=True)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_prompt(sections, contract)}]
    total = {"seconds": 0.0, "cost_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
    path = os.path.join(out_dir, "candidate.rego")
    for attempt in range(repair + 1):
        r = llm.complete(model, msgs)
        for k in total: total[k] += (r.get(k) or 0)
        rego, doubts = parse(r["text"])
        open(path, "w").write(rego)
        ok, err = opa.check(path)
        if ok or attempt == repair: break
        msgs += [{"role": "assistant", "content": r["text"]},
                 {"role": "user", "content": f"opa check failed:\n{err}\nFix it and reply in the same two block format."}]
    json.dump(doubts, open(os.path.join(out_dir, "doubts.json"), "w"), indent=2)
    meta = {"model": model, "compiles": ok, "attempts": attempt + 1, **total}
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"), indent=2)
    return path, meta

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--sections", default="runs/sections.json")
    ap.add_argument("--contract", default="runs/contract.json"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    p, m = run_once(a.model, json.load(open(a.sections)), json.load(open(a.contract)), a.out)
    print(p, m)

if __name__ == "__main__":
    main()
