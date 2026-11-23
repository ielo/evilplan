"""Run N extractions per model, score each one, write runs/<stamp>/summary.csv with mean and spread."""
import argparse, csv, json, os, statistics, time
from . import extract, score

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True); ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--key", default="key/wealth_policy.rego"); ap.add_argument("--cases", default="runs/cases.jsonl")
    ap.add_argument("--sections", default="runs/sections.json"); ap.add_argument("--contract", default="runs/contract.json")
    a = ap.parse_args(argv)
    stamp = time.strftime("%Y%m%d-%H%M%S"); root = f"runs/{stamp}"
    secs, con = json.load(open(a.sections)), json.load(open(a.contract))
    cases = [json.loads(l) for l in open(a.cases) if l.strip()]
    rows = []
    for m in a.models:
        for k in range(a.runs):
            d = f"{root}/{m}/run_{k+1}"
            p, meta = extract.run_once(m, secs, con, d)
            r = score.score(a.key, p, cases, "key/rule_inventory.csv")
            json.dump(r, open(f"{d}/score.json", "w"), indent=2)
            rows.append({"model": m, "run": k + 1, "compiles": r["compiles"], "pass_rate": r["pass_rate"],
                         "wrong_allow": r.get("critical_wrong_allow"), "rule_coverage": r.get("rule_coverage"),
                         "doubts": len(json.load(open(f"{d}/doubts.json"))), "seconds": round(meta["seconds"], 1), "cost_usd": meta["cost_usd"]})
            print(rows[-1])
    os.makedirs(root, exist_ok=True)
    with open(f"{root}/summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    for m in a.models:
        pr = [r["pass_rate"] for r in rows if r["model"] == m]
        print(f"{m}: mean={statistics.mean(pr):.1%} min={min(pr):.1%} max={max(pr):.1%} stdev={statistics.pstdev(pr):.3f}")

if __name__ == "__main__":
    main()
