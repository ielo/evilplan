import json, shutil, pathlib, pytest
from ruleforge import intake, contract, gen_inputs, score

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = str(ROOT / "key/wealth_policy.rego")
PDF = str(ROOT / "inputs/ACME_Bank_Wealth_Management_Policy.pdf")
needs_opa = pytest.mark.skipif(shutil.which("opa") is None, reason="opa not installed")

def test_intake_finds_34_rules():
    ids = [s["id"] for s in intake.sections(PDF)]
    rules = [i for i in ids if len(i) == 4 and i[1] == "-"]
    assert len(rules) == 34

def test_contract_has_no_logic():
    c = contract.build(open(KEY).read())
    assert "L2" in c["approval_roles"] and len(c["actions"]) == 12
    assert "100000" not in json.dumps(c)  # thresholds stay in the policy text

def test_generator_is_deterministic_and_sized():
    t = open(KEY).read()
    a, b = gen_inputs.generate(t, 300, 1), gen_inputs.generate(t, 300, 1)
    assert a == b and len(a) == 300

@needs_opa
def test_key_scores_100_against_itself():
    cases = gen_inputs.generate(open(KEY).read(), 120, 3)
    assert score.score(KEY, KEY, cases)["pass_rate"] == 1.0

@needs_opa
def test_scorer_catches_a_wrong_threshold(tmp_path):
    mutated = tmp_path / "m.rego"
    mutated.write_text(open(KEY).read().replace("amount > 100000", "amount > 900000", 1))
    cases = gen_inputs.generate(open(KEY).read(), 1000, 7)
    r = score.score(KEY, str(mutated), cases)
    assert r["pass_rate"] < 1.0 and r["critical_wrong_allow"] + r["less_strict_than_key"] > 0

@needs_opa
def test_scorer_reports_compile_failure(tmp_path):
    bad = tmp_path / "bad.rego"; bad.write_text("package acme.wealth\nresult := {")
    r = score.score(KEY, str(bad), [{"action": "x"}])
    assert r["compiles"] is False and r["pass_rate"] == 0.0
