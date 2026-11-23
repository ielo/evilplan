"""Generate test inputs from the key's own fields: thresholds from the key, flag polarity from the key,
roles and actions from the key. The expected result is never written here; it comes from running the key."""
import argparse, json, random, re, os, itertools
from .contract import build

def thresholds(text):
    vals = {float(v.replace("_", "")) for v in re.findall(r"[<>]=?\s*(\d[\d_]*(?:\.\d+)?)", text)}
    return sorted(int(v) if v == int(v) else v for v in vals)

def polarity(text, flags):
    good = {}
    for f in flags:
        total = len(re.findall(r'truth\("%s"\)' % f, text))
        neg = len(re.findall(r'not truth\("%s"\)' % f, text))
        good[f] = neg * 2 >= total  # mostly used as "must be true": a good fact
    return good

def appr(role, rid="wm-42", **kw):
    d = {"role": role, "actor_id": role.lower() + "-1", "valid": True, "beneficiary": False, "initiator": False}
    d.update(kw); return d

def generate(rego_text, n=1000, seed=7):
    rnd = random.Random(seed)
    c = build(rego_text)
    th = thresholds(rego_text)
    big = sorted({max(t + d, 0) for t in th if t >= 1000 for d in (-1, 0, 1)} | {0, 1000})
    small = sorted({max(t + d, 0) for t in th if t < 1000 for d in (-1, 0, 1)})
    good = polarity(rego_text, c["boolean_flags"])
    roles, actions = c["approval_roles"], c["actions"]
    other_nums = [f for f in c["numeric_fields"] if f not in ("amount_usd", "aggregate_amount_usd")]

    def base(action, amount=50000):
        i = {"policy_version": "1.0", "action": action, "requester_id": "wm-42", "amount_usd": amount,
             "aggregate_amount_usd": amount, "daily_external_total_usd": amount, "approvals": []}
        for f in c["boolean_flags"]:
            i[f] = good[f]
        return i

    cats = {"sweep": [], "flip": [], "numeric": [], "adversarial": [], "random": []}
    for a in actions:
        for amt in big:
            for label in ("none", "all", "all_but_one"):
                i = base(a, amt)
                rs = roles if label == "all" else (rnd.sample(roles, len(roles) - 1) if label == "all_but_one" else [])
                i["approvals"] = [appr(r) for r in rs]
                cats["sweep"].append(i)
    for f in c["boolean_flags"]:
        for a in rnd.sample(actions, min(4, len(actions))):
            i = base(a, rnd.choice(big)); i[f] = not good[f]
            if rnd.random() < .5: i["approvals"] = [appr(r) for r in roles]
            cats["flip"].append(i)
    for f in other_nums:
        pool = small if (small and f.endswith(("pct", "days", "percent", "ratio"))) else (small + big)
        for a in rnd.sample(actions, min(2, len(actions))):
            for v in rnd.sample(pool, min(5, len(pool))):
                i = base(a, rnd.choice(big)); i[f] = v
                i["approvals"] = [appr(r) for r in roles] if rnd.random() < .5 else []
                cats["numeric"].append(i)
    top = max(big)
    for a in actions:
        for kind in ("self", "invalid", "beneficiary", "initiator"):
            i = base(a, top)
            ap = []
            for r in roles:
                if kind == "self": ap.append(appr(r, actor_id="wm-42"))
                elif kind == "invalid": ap.append(appr(r, valid=False))
                elif kind == "beneficiary": ap.append(appr(r, beneficiary=True))
                else: ap.append(appr(r, initiator=True))
            i["approvals"] = ap; cats["adversarial"].append(i)
        for kind in c["exception_kinds"]:
            for v in ("1.0", "0.9"):
                for valid in (True, False):
                    i = base(a, top); i["approvals"] = [appr(r) for r in roles]
                    i["exceptions"] = [{"kind": kind, "valid": valid, "policy_version": v}]
                    cats["adversarial"].append(i)
    cats["adversarial"] += [
        {**base("external_transfer"), "action": "wire_to_mars"},
        {**base("external_transfer"), "policy_version": "2.0"},
        {**base("external_transfer", -5)},
        {**base("external_transfer"), "amount_usd": "lots", "aggregate_amount_usd": "lots"},
    ]
    for f in c["core_fields"]:
        i = base("external_transfer"); i.pop(f, None); cats["adversarial"].append(i)
    for _ in range(600):
        i = base(rnd.choice(actions), rnd.choice(big))
        for f in c["boolean_flags"]:
            if rnd.random() < .12: i[f] = not good[f]
        i["approvals"] = [appr(r) for r in roles if rnd.random() < .6]
        cats["random"].append(i)

    quota = {"sweep": .33, "flip": .25, "numeric": .12, "adversarial": .10, "random": .20}
    out = []
    for k, items in cats.items():
        q = int(n * quota[k])
        out += rnd.sample(items, min(q, len(items)))
    seen, uniq = set(), []
    for i in out:
        s = json.dumps(i, sort_keys=True)
        if s not in seen: seen.add(s); uniq.append(i)
    pool = [i for k in cats.values() for i in k if json.dumps(i, sort_keys=True) not in seen]
    rnd.shuffle(pool)
    for i in pool:
        if len(uniq) >= n: break
        uniq.append(i)
    return uniq[:n]

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rego"); ap.add_argument("-n", type=int, default=1000); ap.add_argument("--seed", type=int, default=7); ap.add_argument("-o", required=True)
    a = ap.parse_args(argv)
    cases = generate(open(a.rego).read(), a.n, a.seed)
    os.makedirs(os.path.dirname(a.o) or ".", exist_ok=True)
    with open(a.o, "w") as f:
        for c in cases: f.write(json.dumps(c) + "\n")
    print(f"{len(cases)} cases -> {a.o}")

if __name__ == "__main__":
    main()
