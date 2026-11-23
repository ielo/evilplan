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

## Step by step (macOS, 16 GB, local model, no API key)

**1. Tools**
```bash
brew install opa ollama python@3.12
git clone git@github.com:ielo/evilplan.git && cd evilplan
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # includes litellm[proxy]
```
Use Python 3.12 or 3.13. Python 3.15 is too new for some dependencies.

**2. Check the harness without any model**
```bash
make check test                             # key compiles, 6 tests pass
make intake contract cases score-key        # key vs itself must print pass_rate=100.0%
```

**3. A local model**
```bash
ollama pull qwen2.5-coder:7b                # the Ollama app already serves on :11434
curl -s localhost:11434                     # "Ollama is running"
```

**4. Fast path, no gateway**
```bash
make bench MODELS=ollama_chat/qwen2.5-coder:7b RUNS=1
```

**5. Through the LiteLLM gateway**
```bash
cp .env.example .env                        # edit the two keys, any value starting with sk-
make proxy                                  # terminal A. Note the port it prints (it may not be 4000)
```
Terminal B:
```bash
set -a; source .env; set +a
export LITELLM_BASE_URL=http://localhost:<port>
curl -s $LITELLM_BASE_URL/v1/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" -d '{"model":"local-small","messages":[{"role":"user","content":"say ok"}]}'
make bench MODELS=local-small RUNS=1
```

**6. Read the result** in `runs/<date>/`: `summary.csv` (one line per run), and per run `candidate.rego`,
`doubts.json` (ambiguities and conflicts the model raised) and `score.json` (pass rate, wrong ALLOW, missing rules, sample failures).
Small local models often fail to compile. That is a valid result and `score.json` shows the `opa check` error.

## Scoring
Pass rate (decision plus missing approvals match the key), wrong ALLOW count (worst error), less strict and stricter
than the key, rule coverage (34 labeled rules), compile rate, doubts raised, seconds per run, spread across runs.

## Layout
| Path | What |
|---|---|
| `inputs/` | What the extractor may read: the policy PDF |
| `key/` | The answer key: Rego, rule inventory, example input, owner reference. `PATCHES.md` lists two fixes needed to compile it |
| `src/ruleforge/` | `intake`, `contract`, `gen_inputs`, `opa`, `score`, `llm`, `extract`, `bench` |
| `litellm/config.yaml` | Gateway models. Local Ollama by default, hosted models as optional blocks |
| `runs/` | Generated files and results, git ignored |

## Troubleshooting (all seen in practice)
| Symptom | Cause and fix |
|---|---|
| `Missing dependency websockets` | Install the proxy extra: `pip install 'litellm[proxy]'` |
| `Malformed API Key` | `$LITELLM_MASTER_KEY` is empty in this terminal. Run `set -a; source .env; set +a` |
| `No connected db` | The key sent differs from the one the proxy started with. Restart the proxy from the same `.env` |
| `Missing Anthropic API Key` | A hosted model alias was called. Use `local-small`, or add the key to `.env` and restart |
| `address already in use` on `ollama serve` | Ollama is already running. Nothing to fix |
| Connection refused on the gateway | Wrong port. Use the one `make proxy` printed |
| Rego cut off or ignores late rules | Context window too small. Keep `num_ctx: 16384` (proxy) or `OLLAMA_NUM_CTX` (direct) |
| `git push` permission denied (publickey) | No SSH key on GitHub. Use HTTPS with a fine grained token |

## Known limits
- The key is a draft, unadjudicated. Ambiguities (AMB-01 to 07) and conflicts (CON-01 to 04) are reported in `doubts.json`, not scored as failures yet.
- A 7B local model proves the pipeline, not the hypothesis. Frontier models need an approved route (cloud gateway or internal). Only `litellm/config.yaml` changes.
- The extractor runs one shot on the whole PDF. A 500 page policy needs chunking by section.
- Generated inputs use flag polarity inferred from the key. Review `gen_inputs.py` with the policy owner.
