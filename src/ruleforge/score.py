"""Run the same inputs through the key and a candidate Rego, then compare decision and missing approvals."""
import argparse, json, re, collections, os
from . import opa

ORDER = {"ALLOW": 0, "REQUIRE_APPROVAL": 1, "HOLD": 2, "DENY": 3}

def norm(r):
    if "error" in r: return ("ERROR", ())
    miss = tuple(sorted((m.get("rule_id", ""), m.get("role", "")) for m in r.get("missing_approvals", [])))
    return (r.get("decision", "UNDEFINED"), miss)

def rule_ids(path):
    return set(re.findall(r'"([A-Z]-\d{2})"', open(path).read()))

def score(key, cand, cases, inventory=None):
    ok, msg = opa.check(cand)
    rep = {"candidate": cand, "cases": len(cases), "compiles": ok}
    if not ok:
        rep.update(pass_rate=0.0, compile_error=msg[:500]); return rep
    kr, cr = opa.evaluate(key, cases), opa.evaluate(cand, cases)
    passed, dec_ok, critical, lenient, strict = 0, 0, 0, 0, 0
    conf, by_action, fails = collections.Counter(), collections.defaultdict(lambda: [0, 0]), []
    for inp, k, c in zip(cases, kr, cr):
        nk, nc = norm(k), norm(c)
        a = inp.get("action", "?"); by_action[a][1] += 1
        conf[(nk[0], nc[0])] += 1
        if nk[0] == nc[0]: dec_ok += 1
        if nk == nc:
            passed += 1; by_action[a][0] += 1
        else:
            if nc[0] == "ALLOW" and nk[0] != "ALLOW": critical += 1
            elif ORDER.get(nc[0], 9) < ORDER.get(nk[0], 9): lenient += 1
            elif nc[0] == nk[0] and set(nc[1]) < set(nk[1]): lenient += 1  # same decision, fewer approvals demanded
            else: strict += 1
            if len(fails) < 10: fails.append({"input": inp, "key": nk[0], "candidate": nc[0], "key_missing": nk[1], "cand_missing": nc[1]})
    n = len(cases)
    kids = rule_ids(key) if not inventory else {l.split(",")[0] for l in open(inventory).read().splitlines()[1:] if l}
    cids = rule_ids(cand)
    rep.update(pass_rate=passed / n, decision_match_rate=dec_ok / n, critical_wrong_allow=critical,
               less_strict_than_key=lenient, stricter_than_key=strict,
               rule_coverage=len(kids & cids) / max(len(kids), 1), rules_missing=sorted(kids - cids),
               by_action={a: v[0] / v[1] for a, v in by_action.items()},
               confusion={f"{a}->{b}": v for (a, b), v in sorted(conf.items())}, sample_failures=fails)
    return rep

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True); ap.add_argument("--candidate", required=True); ap.add_argument("--cases", required=True)
    ap.add_argument("--inventory", default="key/rule_inventory.csv"); ap.add_argument("-o")
    a = ap.parse_args(argv)
    cases = [json.loads(l) for l in open(a.cases) if l.strip()]
    r = score(a.key, a.candidate, cases, a.inventory if os.path.exists(a.inventory) else None)
    if a.o: json.dump(r, open(a.o, "w"), indent=2)
    print(f"compiles={r['compiles']} pass_rate={r['pass_rate']:.1%}", end="")
    if r["compiles"]:
        print(f" decision_match={r['decision_match_rate']:.1%} wrong_ALLOW={r['critical_wrong_allow']} less_strict={r['less_strict_than_key']} stricter={r['stricter_than_key']} rule_coverage={r['rule_coverage']:.0%}")
    else:
        print("\n" + r["compile_error"])
    return r

if __name__ == "__main__":
    main()
