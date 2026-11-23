# RuleForge (the Evil Plan)

Hypothesis: an LLM can turn a human policy into Rego, and OPA then enforces it outside the agent.
This repo is the experiment harness. **The reference Rego is the answer key.**

```
policy PDF ──► intake ──► sections.json ─┐
key fields ──► contract.json ────────────┼─► LLM extractor ─► candidate.rego + doubts.json
                                         │   (LiteLLM library ─► Ollama)      │
key Rego ──► gen_inputs ──► ~1000 cases ─┴────────────────► opa eval (key vs candidate) ──► score
```

The extractor sees the PDF and the input contract (field names, types, roles, actions). It never sees the key's logic.
Expected results come from running the key on the generated inputs, so the test is not circular.

## Status (update this section as results arrive)

| Piece | State |
|---|---|
| PDF intake (34 labeled rules found) | Working |
| Input contract and 1,000 case generator | Working |
| Scorer (decision and missing approvals vs the key) | Working. Key against itself scores 100%. A mutated key is caught by the tests |
| Tests (`make test`) | 6 passing |
| LLM extraction with a local model | **Not measured yet.** Wired up, no result recorded |
| Hosted models (Anthropic, Bedrock and others) | Not used. No approved access. Config blocks are commented out |
| Human control group | Not started |
| Hypothesis (90% on about 1,000 tests) | **Untested.** A 7B local model proves the pipeline, not the hypothesis |

## Where LiteLLM fits (and where it does not)

- **As a library (the default path):** `src/ruleforge/llm.py` calls `litellm.completion(...)`. It gives one call shape for any
  provider, so moving from Ollama to a hosted model means changing the model string. It also reports cost for hosted models.
  With a single local model this adds little over calling Ollama directly.
- **As a proxy (optional):** `make proxy` starts a shared endpoint with aliases, keys, budgets and logs. It is only worth it
  when several people or several providers share it. **You do not need it to run the experiment.**
- LiteLLM routes model calls. It does not decide whether an agent action may run. That is OPA's job.

## Step by step (macOS, 16 GB, local model, no API key)

**1. Tools**
```bash
brew install opa ollama python@3.12
git clone https://github.com/ielo/evilplan.git && cd evilplan
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Use Python 3.12 or 3.13. Newer versions may lack prebuilt packages for some dependencies.

**2. Check the harness without any model**
```bash
make check test                             # key compiles, 6 tests pass (about 40 seconds)
make intake contract cases score-key        # last line must show pass_rate=100.0%
```

**3. A local model**
```bash
ollama pull qwen2.5-coder:7b                # the Ollama app already serves on :11434
curl -s localhost:11434                     # "Ollama is running"
```

**4. Run the experiment (default path, no proxy)**
```bash
make bench MODELS=ollama_chat/qwen2.5-coder:7b RUNS=1
```
Expect minutes per attempt on a 16 GB machine. If the Rego does not compile, the extractor retries once with the `opa check`
error, so time can double. Close heavy apps while it runs.

**5. Read the result** in `runs/<date>/`: `summary.csv` (one line per run), and per run `candidate.rego`,
`doubts.json` (ambiguities and conflicts the model raised) and `score.json` (pass rate, wrong ALLOW, missing rules, sample failures).
Small local models often fail to compile or break the two block answer format. That is a valid result, and `score.json` keeps the `opa check` error.

**Optional: shared LiteLLM proxy**
```bash
cp .env.example .env                        # set two keys, any value starting with sk-
make proxy                                  # terminal A. Use the port it prints, it may not be 4000
```
Terminal B:
```bash
set -a; source .env; set +a
export LITELLM_BASE_URL=http://localhost:<port>
make bench MODELS=local-small RUNS=1        # aliases from litellm/config.yaml work only through the proxy
```
`num_ctx: 16384` in `litellm/config.yaml` is meant to give Ollama a large enough window. We have not confirmed that the
proxy honors it. If long policies look truncated, create a model with the window fixed:
`printf 'FROM qwen2.5-coder:7b\nPARAMETER num_ctx 16384\n' > Modelfile && ollama create qwen-16k -f Modelfile`.

## Scoring
Pass rate (decision plus missing approvals match the key), wrong ALLOW count (worst error), less strict and stricter
than the key, rule coverage (34 labeled rules), compile rate, doubts raised, seconds per run, spread across runs.
Cost is only meaningful for hosted models. For a local model, read time.

## Layout
| Path | What |
|---|---|
| `inputs/` | What the extractor may read: the policy PDF |
| `key/` | The answer key: Rego, rule inventory, example input, owner reference. `PATCHES.md` lists two fixes needed to compile it |
| `src/ruleforge/` | `intake`, `contract`, `gen_inputs`, `opa`, `score`, `llm`, `extract`, `bench` |
| `litellm/config.yaml` | Only for the optional proxy. Local Ollama alias, hosted models as commented blocks |
| `runs/` | Generated files and results, git ignored |

## Troubleshooting (all seen in practice)

| Symptom | Cause and fix |
|---|---|
| `No module named ruleforge.intake` | `src/ruleforge` is incomplete. Re-extract the full project |
| `No module named pymupdf` | Dependencies not installed in this venv. Run `pip install -r requirements.txt` |
| `address already in use` on `ollama serve` | Ollama is already running. Nothing to fix |
| `git push` permission denied (publickey) | No SSH key on GitHub. Use HTTPS with a fine grained token |
| Rego fails with `allow {` or missing `if` | The model wrote old Rego syntax. The prompt asks for v1. Check `compile_error` in `score.json` |
| Rego cut off or ignores late rules | Context window too small. Set `OLLAMA_NUM_CTX` (direct path) or fix `num_ctx` (proxy) |

Only with the optional proxy:

| Symptom | Cause and fix |
|---|---|
| `Missing dependency websockets` | Install the proxy extra: `pip install 'litellm[proxy]'` (already in `requirements.txt`) |
| `Malformed API Key` | `$LITELLM_MASTER_KEY` is empty in this terminal. Run `set -a; source .env; set +a` |
| `No connected db` | The key sent differs from the one the proxy started with. Restart the proxy from the same `.env` |
| `Missing Anthropic API Key` | A hosted alias was called. Use `local-small`, or add the key to `.env` and restart |
| Connection refused | Wrong port. Use the one `make proxy` printed |

## Known limits
- The key is a draft, unadjudicated. Ambiguities (AMB-01 to 07) and conflicts (CON-01 to 04) are reported in `doubts.json`, not scored as failures yet.
- The extractor runs one shot on the whole PDF. A 500 page policy needs chunking by section.
- Generated inputs use flag polarity inferred from the key. Review `gen_inputs.py` with the policy owner.
- The input contract is derived from the key, so the extractor knows field names. In a real bank that contract would come from upstream data services. Confirm this choice with the key author.
- Frontier models need an approved route (cloud gateway or internal). Only the model string and `litellm/config.yaml` change.
