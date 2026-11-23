PY=PYTHONPATH=src python3 -m
KEY=key/wealth_policy.rego

.PHONY: check intake contract cases score-key test proxy bench
check:            ## the key must compile
	opa check $(KEY)
intake:           ## PDF -> sections.json
	$(PY) ruleforge.intake inputs/ACME_Bank_Wealth_Management_Policy.pdf -o runs/sections.json
contract:         ## key fields -> contract.json (names and types only, no logic)
	$(PY) ruleforge.contract $(KEY) -o runs/contract.json
cases:            ## ~1000 inputs generated from the key's own fields
	$(PY) ruleforge.gen_inputs $(KEY) -n 1000 --seed 7 -o runs/cases.jsonl
score-key:        ## sanity check: the key scored against itself must be 100%
	$(PY) ruleforge.score --key $(KEY) --candidate $(KEY) --cases runs/cases.jsonl
test:
	PYTHONPATH=src python3 -m pytest -q

MODELS ?= ollama_chat/qwen2.5-coder:7b
RUNS ?= 1
proxy:            ## OPTIONAL shared LiteLLM proxy. Loads .env first. Note the port it prints.
	set -a; . ./.env; set +a; litellm --config litellm/config.yaml
bench:            ## default path: MODELS=ollama_chat/<model>. Aliases like local-small need the proxy and LITELLM_BASE_URL
	$(PY) ruleforge.bench --models $(MODELS) --runs $(RUNS)
