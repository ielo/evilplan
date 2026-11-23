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
    t0 = time.time()
    r = litellm.completion(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kw)
    try:
        cost = litellm.completion_cost(completion_response=r)
    except Exception:
        cost = None
    u = r.usage
    return {"text": r.choices[0].message.content, "seconds": time.time() - t0, "cost_usd": cost,
            "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
