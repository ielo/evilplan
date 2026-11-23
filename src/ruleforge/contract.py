"""Derive the input contract (field names, types, actions, roles) from the key.
Names and types only. No thresholds, no logic, so the extractor still has to read the policy."""
import argparse, json, re, os

def build(rego_text):
    flags = sorted(set(re.findall(r'truth\("([a-z_0-9]+)"\)', rego_text)))
    nums, other = {}, {}
    for k, d in re.findall(r'value\("([a-z_0-9]+)",\s*([^)]*)\)', rego_text):
        d = d.strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", d): nums[k] = "number"
        elif d == "[]": other[k] = "array"
        elif d.startswith('"'): other[k] = "string"
        elif d in ("true", "false"): other[k] = "boolean"
    numbers = sorted(set(nums) | {"amount_usd", "aggregate_amount_usd"})
    m = re.search(r'not action in \{([^}]*)\}', rego_text)
    actions = re.findall(r'"([a-z_]+)"', m.group(1)) if m else []
    roles = sorted(set(re.findall(r'"role":\s*"([A-Za-z0-9]+)"', rego_text)) | set(re.findall(r'approved\("([A-Za-z0-9]+)"\)', rego_text)))
    kinds = sorted(set(re.findall(r'has_exception\("([a-z_]+)"\)', rego_text)))
    return {
        "entrypoint": "data.acme.wealth.result",
        "package": "acme.wealth",
        "decisions": ["ALLOW", "REQUIRE_APPROVAL", "HOLD", "DENY"],
        "precedence": "DENY > HOLD > REQUIRE_APPROVAL > ALLOW",
        "result_shape": {"decision": "string", "required_approvals": "array of {rule_id, role}",
                         "missing_approvals": "array of {rule_id, role}", "findings": "array", "executable": "boolean"},
        "boolean_flags": flags, "numeric_fields": numbers, "other_fields": other,
        "core_fields": ["policy_version", "action", "requester_id", "amount_usd", "aggregate_amount_usd", "approvals"],
        "actions": actions, "approval_roles": roles, "exception_kinds": kinds,
        "approval_object": {"role": "string", "actor_id": "string", "valid": "bool", "beneficiary": "bool", "initiator": "bool"},
        "exception_object": {"kind": "string", "valid": "bool", "policy_version": "string"},
    }

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("rego"); ap.add_argument("-o", required=True)
    a = ap.parse_args(argv)
    c = build(open(a.rego).read())
    os.makedirs(os.path.dirname(a.o) or ".", exist_ok=True)
    json.dump(c, open(a.o, "w"), indent=2)
    print(f"{len(c['boolean_flags'])} flags, {len(c['numeric_fields'])} numeric, {len(c['actions'])} actions, roles={c['approval_roles']} -> {a.o}")

if __name__ == "__main__":
    main()
