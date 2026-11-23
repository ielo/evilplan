# RuleForge (the Evil Plan)

Hypothesis: an LLM can turn a human policy into Rego, and OPA then enforces it outside the agent.
This repo is the experiment harness. **The reference Rego is the answer key.**

```
policy PDF ──► intake ──► sections.json ─┐
key fields ──► contract.json ────────────┼─► LLM extractor (LiteLLM) ─► candidate.rego + doubts.json
                                         │                                   │
key Rego ──► gen_inputs ──► ~1000 cases ─┴──────────────► opa eval (key vs candidate) ──► score
```

The extractor sees the PDF and the input contract (field names, types, roles, actions). It never sees the key's logic.
Expected results come from running the key on the generated inputs, so the test is not circular.

## Quick start
```bash
pip install -r requirements.txt        # needs the opa CLI on PATH
make check test                        # key compiles, harness tests pass
make intake contract cases score-key   # key vs itself must print 100%
export ANTHROPIC_API_KEY=...           # or run the LiteLLM proxy: litellm --config litellm/config.yaml
PYTHONPATH=src python3 -m ruleforge.bench --models haiku sonnet --runs 3
```

## Layout
| Path | What |
|---|---|
| `inputs/` | What the extractor may read: the policy PDF |
| `key/` | The answer key: Rego, rule inventory, example input, owner reference. `PATCHES.md` lists two fixes needed to compile it |
| `src/ruleforge/` | `intake`, `contract`, `gen_inputs`, `opa`, `score`, `llm`, `extract`, `bench` |
| `litellm/config.yaml` | Model aliases for the gateway: haiku, sonnet, opus, fable |
| `runs/` | Generated files and results, git ignored |

## Scoring
Pass rate (decision plus missing approvals match the key), wrong ALLOW count (worst error), less strict and stricter
than the key, rule coverage (34 labeled rules), compile rate, doubts raised, seconds and cost per run, spread across runs.

## Known limits
- The key is a draft, unadjudicated. Ambiguities (AMB-01 to 07) and conflicts (CON-01 to 04) are reported in `doubts.json`, not scored as failures yet.
- The extractor runs one shot on the whole PDF. A 500 page policy needs chunking by section.
- Generated inputs use flag polarity inferred from the key. Review `gen_inputs.py` with the policy owner.
