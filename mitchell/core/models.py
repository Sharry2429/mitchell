AICREDITS_BASE_URL = "https://api.aicredits.in/v1"

MODEL_TIERS = {
    "ui_vision":      "bytedance/ui-tars-1.5-7b",
    "general_vision": "openai/gpt-5.6-luna",
    "base":           "openai/gpt-5.6-luna",
    "mid":            "openai/gpt-5.6-terra",
    "top":            "openai/gpt-5.6-sol",
    "seed":           "bytedance-seed/seed-1.6-flash",
    "deepseek":       "deepseek/deepseek-v4-flash",
    "gemini":         "google/gemini-flash-latest",
    # Role-pinned models (model-routing plan):
    "planner":        "openai/gpt-5.6-luna",   # Planner: GPT-5.6 Luna
}

# Executor chain (model-routing plan): GPT-OSS 120B -> GPT-OSS 20B ->
# Llama 3.3 70B on Groq, with AiCredits (DeepSeek/configured) as the final net.
EXECUTOR_CHAIN = [
    {"provider": "groq", "model": "openai/gpt-oss-120b"},   # primary
    {"provider": "groq", "model": "openai/gpt-oss-20b"},    # fallback 1
    {"provider": "groq", "model": "llama-3.3-70b-versatile"},  # fallback 2
    # fallback 3 = AiCredits configured/DeepSeek model (added at call time)
]

# Real per-model pricing, USD per 1M tokens (input/output).
# These are structural — the budget meter must read REAL costs from the routing
# table, not a flat placeholder. Values are per-model overrides; fall back to
# DEFAULT_PRICING when a tier/model is not listed. Set prices precisely later
# from the actual provider's bill; the mechanism is what matters here.
DEFAULT_PRICING = {"input": 0.10, "output": 0.30}

MODEL_PRICING = {
    "openai/gpt-5.6-luna":          {"input": 0.15,  "output": 0.60},
    "openai/gpt-5.6-terra":         {"input": 0.30,  "output": 1.20},
    "openai/gpt-5.6-sol":           {"input": 0.60,  "output": 2.40},
    "bytedance/ui-tars-1.5-7b":     {"input": 0.10,  "output": 0.20},
    "bytedance-seed/seed-1.6-flash":{"input": 0.05,  "output": 0.15},
    "deepseek/deepseek-v4-flash":   {"input": 0.02,  "output": 0.05},
    "google/gemini-flash-latest":   {"input": 0.075, "output": 0.30},
    # Groq executor chain (per-model pricing for the budget meter)
    "openai/gpt-oss-120b":          {"input": 0.10,  "output": 0.40},
    "openai/gpt-oss-20b":           {"input": 0.05,  "output": 0.20},
    "llama-3.3-70b-versatile":      {"input": 0.59,  "output": 0.79},
}


def pricing_for(model: str) -> dict:
    """Return {input, output} USD-per-1M-token pricing for a model."""
    return MODEL_PRICING.get(model, DEFAULT_PRICING)


# Roles that are capability-pinned and must NEVER be downgraded to a text model.
_VISION_ROLES = ("ui_vision", "general_vision")
_BUDGET_LOW = 1.0  # $ remaining threshold at which cost-aware downgrade kicks in


def select_model(role: str, remaining_budget: float | None = None) -> str:
    """Route a role to a model, downgrading high-volume roles when budget is low.

    Vision/UI roles are capability-pinned and are never swapped to a text model
    (routing a coordinate-grounding task to a text model is a category error).
    Everything else falls back to the cheapest model in the routing table when
    remaining budget drops below the threshold.
    """
    base = MODEL_TIERS[role]
    if role in _VISION_ROLES or remaining_budget is None:
        return base
    if remaining_budget < _BUDGET_LOW:
        cheapest = min(MODEL_PRICING, key=lambda m: MODEL_PRICING[m]["output"])
        return cheapest
    return base
