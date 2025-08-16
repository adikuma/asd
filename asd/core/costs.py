import json
import os
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


def _fmt_usd(x: float) -> str:
    return f"${x:,.4f}" if x < 1 else f"${x:,.2f}"


def fmt_usd(x: float) -> str:
    # public helper for UI formatting
    return _fmt_usd(x)


def _model_key(provider: str, model: str) -> str:
    p = (provider or "").strip().lower()
    m = (model or "").strip().lower()
    return f"{p}:{m}"


def get_active_model_provider() -> Tuple[str, str]:
    if os.getenv("GOOGLE_API_KEY"):
        return (
            "google",
            os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        )
    return ("openai", os.getenv("OPENAI_MODEL", "o4-mini"))


# NOTE:
# - gpt-4o output is set to $20/M based on openai website
# - gpt-4.1 rates are consistent across current guides ($2/$8 and $0.40/$1.60).
# - o4-mini from OpenAI community + OpenRouter.
# - gemini 2.5 pro is tiered based on prompt size per official coverage (annoying)
DEFAULT_PRICING: Dict[str, Dict[str, Any]] = {
    "openai": {
        "gpt-4o": {"in": 2.50, "out": 10.00},
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "gpt-4.1": {"in": 2.00, "out": 8.00},
        "gpt-4.1-mini": {"in": 0.40, "out": 1.60},
        "o4-mini": {"in": 1.10, "out": 4.40},
    },
    "google": {
        "gemini-2.5-pro": {
            "tiered": True,
            "tiers": {
                "in": [(200_000, 1.25), (None, 2.50)],
                "out": [(200_000, 10.00), (None, 15.00)],
            },
        },
        "gemini-2.5-flash": {"in": 0.35, "out": 1.05},
        "gemini-2.0-flash": {"in": 0.35, "out": 1.05},
    },
}


def _load_overrides() -> Dict[str, Dict[str, Any]]:
    s = os.getenv("ASD_PRICING_OVERRIDES")
    if not s:
        return {}
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _merge_pricing(
    base: Dict[str, Dict[str, Any]],
    overrides: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    merged = {**base}
    for provider, models in overrides.items():
        if provider not in merged:
            merged[provider] = {}
        for m, v in models.items():
            merged[provider][m] = v
    return merged


PRICING = _merge_pricing(DEFAULT_PRICING, _load_overrides())


def _match_model(provider: str, model: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    p = provider.strip().lower()
    m = model.strip().lower()
    models = PRICING.get(p, {})
    if m in models:
        return m, models[m]
    for k in models.keys():
        if m.startswith(k) or k in m:
            return k, models[k]
    return m, None


def _rate_per_token_per_million(x: float) -> float:
    # convert $/1M to $/token
    return float(x) / 1_000_000.0


def _pick_tier(
    pairs: List[Tuple[Optional[int], float]],
    prompt_tokens: Optional[int],
) -> float:
    if prompt_tokens is None:
        return pairs[0][1]
    for thr, rate in pairs:
        if thr is None:
            return rate
        if prompt_tokens <= thr:
            return rate
    return pairs[-1][1]


def get_rates(
    provider: str,
    model: str,
    prompt_tokens: Optional[int] = None,
) -> Optional[Tuple[float, float]]:
    _, spec = _match_model(provider, model)
    if not spec:
        return None
    if spec.get("tiered"):
        in_rate = _pick_tier(spec["tiers"]["in"], prompt_tokens)
        out_rate = _pick_tier(spec["tiers"]["out"], prompt_tokens)
        return in_rate, out_rate
    return spec["in"], spec["out"]


def compute_cost_usd(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Optional[float]:
    rates = get_rates(provider, model, prompt_tokens)
    if not rates:
        return None
    in_per_m, out_per_m = rates
    return prompt_tokens * _rate_per_token_per_million(
        in_per_m
    ) + completion_tokens * _rate_per_token_per_million(out_per_m)


# this class is a tracker for the usage of the model
class TokenTracker:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.totals: Dict[str, Dict[str, Any]] = {}
        self.last: Optional[Dict[str, Any]] = None

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Optional[float],
    ) -> None:
        key = _model_key(provider, model)
        if key not in self.totals:
            self.totals[key] = {
                "provider": provider,
                "model": model,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0,
                "calls": 0,
            }
        t = self.totals[key]
        t["prompt_tokens"] += prompt_tokens
        t["completion_tokens"] += completion_tokens
        t["calls"] += 1
        if cost is not None:
            t["cost"] += cost

        rec = {
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
        }
        self.calls.append(rec)
        self.last = rec

    def grand_totals(self) -> Dict[str, Any]:
        gt = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost": 0.0,
            "calls": 0,
        }
        for v in self.totals.values():
            gt["prompt_tokens"] += v["prompt_tokens"]
            gt["completion_tokens"] += v["completion_tokens"]
            gt["cost"] += v["cost"]
            gt["calls"] += v["calls"]
        return gt


tracker = TokenTracker()


def record_usage(provider: str, model: str, usage: Dict[str, int]) -> None:
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    cost = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)
    tracker.record(provider, model, prompt_tokens, completion_tokens, cost)


def session_usage_snapshot() -> Dict[str, Any]:
    # snapshot suitable for building a small table in the UI
    models: List[Dict[str, Any]] = []
    for key, v in tracker.totals.items():
        models.append(
            {
                "provider": v["provider"],
                "model": v["model"],
                "calls": v["calls"],
                "prompt_tokens": v["prompt_tokens"],
                "completion_tokens": v["completion_tokens"],
                "cost": float(v["cost"]),
            }
        )
    grand = tracker.grand_totals()
    return {"models": models, "grand": grand}


# this class is a callback handler for the usage of the model
class UsageCallback(BaseCallbackHandler):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__()
        self.provider = provider
        self.model = model
        # Debug print to see if callback is created
        print(f"DEBUG: UsageCallback created for {provider}:{model}")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        # Debug print to see if LLM call starts
        print(f"DEBUG: LLM call started for {self.provider}:{self.model}")

    # TODO: add better token estimation
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        prompt = 0
        completion = 0

        # 1) check response.llm_output for usage
        if response.llm_output and isinstance(response.llm_output, dict):
            # openai format
            tu = response.llm_output.get("token_usage") or response.llm_output.get(
                "usage"
            )
            if isinstance(tu, dict):
                prompt = int(tu.get("prompt_tokens") or 0)
                completion = int(tu.get("completion_tokens") or 0)

            # google format in llm_output
            um = response.llm_output.get("usage_metadata") or response.llm_output.get(
                "usageMetadata"
            )
            if isinstance(um, dict):
                prompt = int(um.get("prompt_token_count") or 0)
                completion = int(um.get("candidates_token_count") or 0)

        # 2) check generations for usage metadata
        if prompt == 0 and completion == 0 and response.generations:
            try:
                for gens in response.generations:
                    for gen in gens:
                        # check message for usage_metadata attribute
                        msg = getattr(gen, "message", None)
                        if msg and hasattr(msg, "usage_metadata"):
                            um = msg.usage_metadata
                            if isinstance(um, dict):
                                prompt += int(
                                    um.get("input_tokens")
                                    or um.get("prompt_token_count")
                                    or 0
                                )
                                completion += int(
                                    um.get("output_tokens")
                                    or um.get("candidates_token_count")
                                    or 0
                                )

                        # check response_metadata
                        if (
                            msg
                            and hasattr(msg, "response_metadata")
                            and msg.response_metadata
                        ):
                            meta = msg.response_metadata
                            tu = meta.get("token_usage") or meta.get("usage")
                            if isinstance(tu, dict):
                                prompt += int(tu.get("prompt_tokens") or 0)
                                completion += int(tu.get("completion_tokens") or 0)
                            um = meta.get("usage_metadata") or meta.get("usageMetadata")
                            if isinstance(um, dict):
                                prompt += int(
                                    um.get("input_tokens")
                                    or um.get("prompt_token_count")
                                    or 0
                                )
                                completion += int(
                                    um.get("output_tokens")
                                    or um.get("candidates_token_count")
                                    or 0
                                )
            except Exception as e:
                print(f"DEBUG: Exception parsing generations: {e}")

        # 3) realistic estimation fallback
        if prompt == 0 and completion == 0:
            print("DEBUG: No usage found, using realistic estimation")
            if response.generations and len(response.generations) > 0:
                # estimate based on response length
                total_response_text = ""
                try:
                    for gens in response.generations:
                        for gen in gens:
                            if hasattr(gen, "text"):
                                total_response_text += gen.text or ""
                            elif (
                                hasattr(gen, "message")
                                and gen.message
                                and hasattr(gen.message, "content")
                            ):
                                total_response_text += gen.message.content or ""

                    # better estimation: ~4 characters per token (more accurate than 1-2 tokens total)
                    completion = max(
                        50, len(total_response_text) // 4
                    )  # minimum 50 tokens
                    # for git assistant, prompts are typically 100-500 tokens
                    prompt = max(150, completion // 2)  # minimum 150 tokens for prompts

                    print(
                        f"DEBUG: Estimated tokens based on text length - prompt:{prompt}, completion:{completion}"
                    )
                except Exception as e:
                    print(f"DEBUG: Estimation failed: {e}")
                    # realistic fallback for git planning tasks
                    prompt = 300  # typical git context + intent parsing
                    completion = 200  # typical plan response

        print(f"DEBUG: Final token counts - prompt:{prompt}, completion:{completion}")

        if prompt > 0 or completion > 0:
            record_usage(
                self.provider,
                self.model,
                {
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                },
            )
