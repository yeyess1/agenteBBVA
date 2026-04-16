"""
Utility functions for metrics: cost estimation per LLM provider.
"""

# Gemini pricing per 1M tokens (as of 2025-Q1)
# Source: https://ai.google.dev/pricing
GEMINI_PRICING: dict = {
    "gemini-2.0-flash": {
        "input": 0.075 / 1_000_000,   # $0.075 per 1M input tokens
        "output": 0.30 / 1_000_000,   # $0.30 per 1M output tokens
    },
    "gemini-2.0-flash-lite": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-1.5-pro": {
        "input": 3.50 / 1_000_000,
        "output": 10.50 / 1_000_000,
    },
}


def estimate_gemini_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Estimate cost in USD for a Gemini API call.

    Args:
        model: Gemini model name (e.g., "gemini-2.0-flash")
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Estimated cost in USD, rounded to 8 decimal places
    """
    pricing = GEMINI_PRICING.get(model, GEMINI_PRICING["gemini-2.0-flash"])
    cost = input_tokens * pricing["input"] + output_tokens * pricing["output"]
    return round(cost, 8)
