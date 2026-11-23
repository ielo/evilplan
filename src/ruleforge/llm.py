"""All model calls go through LiteLLM. Point LITELLM_BASE_URL at the proxy to get one gateway for every model,
or leave it unset to call providers directly with the SDK."""
import os, time
import litellm

def complete(model, messages, max_tokens=16000, temperature=0.0):
    kw = {}
    if os.getenv("LITELLM_BASE_URL"):
        kw["api_base"] = os.environ["LITELLM_BASE_URL"]
        kw["api_key"] = os.getenv("LITELLM_MASTER_KEY", "sk-local")
        model = "openai/" + model  # proxy speaks the OpenAI protocol
    elif model.startswith("ollama"):
        kw["api_base"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        kw["num_ctx"] = int(os.getenv("OLLAMA_NUM_CTX", "16384"))  # default window would silently cut the policy
    t0 = time.time()
    r = litellm.completion(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kw)
    try:
        cost = litellm.completion_cost(completion_response=r)
    except Exception:
        cost = None
    u = r.usage
    return {"text": r.choices[0].message.content, "seconds": time.time() - t0, "cost_usd": cost,
            "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
