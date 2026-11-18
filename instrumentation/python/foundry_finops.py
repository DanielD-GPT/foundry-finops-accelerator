import logging
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class UsageEvent:
    team: str
    application: str
    cost_center: str
    environment: str
    user_id: str
    foundry_resource: str
    deployment: str
    model: str
    request_id: str
    trace_id: str
    status_code: int
    success: bool
    prompt_tokens: int
    cached_prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    retry_count: int
    input_per_million: float
    cached_input_per_million: float
    output_per_million: float
    currency: str
    pricing_effective_date: str


def calculate_cost(event: UsageEvent) -> tuple[float, float, float]:
    uncached = max(event.prompt_tokens - event.cached_prompt_tokens, 0)
    input_cost = (
        uncached * event.input_per_million
        + event.cached_prompt_tokens * event.cached_input_per_million
    ) / 1_000_000
    output_cost = event.completion_tokens * event.output_per_million / 1_000_000
    return input_cost, output_cost, input_cost + output_cost


def emit_usage(event: UsageEvent, logger: logging.Logger | None = None) -> None:
    target = logger or logging.getLogger("foundry.finops")
    input_cost, output_cost, total_cost = calculate_cost(event)
    source = asdict(event)
    properties = {
        "schemaVersion": "1.0",
        **{key: value for key, value in source.items() if not key.endswith("_per_million")},
        "costCenter": source["cost_center"],
        "userId": source["user_id"],
        "foundryResource": source["foundry_resource"],
        "requestId": source["request_id"],
        "traceId": source["trace_id"],
        "statusCode": source["status_code"],
        "promptTokens": source["prompt_tokens"],
        "cachedPromptTokens": source["cached_prompt_tokens"],
        "completionTokens": source["completion_tokens"],
        "totalTokens": source["total_tokens"],
        "latencyMs": source["latency_ms"],
        "retryCount": source["retry_count"],
        "estimatedInputCost": input_cost,
        "estimatedOutputCost": output_cost,
        "estimatedTotalCost": total_cost,
        "pricingEffectiveDate": source["pricing_effective_date"],
    }
    for snake_case in (
        "cost_center",
        "user_id",
        "foundry_resource",
        "request_id",
        "trace_id",
        "status_code",
        "prompt_tokens",
        "cached_prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "latency_ms",
        "retry_count",
        "pricing_effective_date",
    ):
        properties.pop(snake_case, None)
    target.info("ai.finops.usage", extra={"custom_dimensions": properties})
