import math

from foundry_finops import UsageEvent, calculate_cost


def test_calculate_cost_handles_cached_tokens():
    event = UsageEvent(
        team="platform",
        application="sample",
        cost_center="cc-1000",
        environment="test",
        user_id="user-001",
        foundry_resource="foundry",
        deployment="gpt-5-mini",
        model="gpt-5-mini",
        request_id="request-1",
        trace_id="trace-1",
        status_code=200,
        success=True,
        prompt_tokens=1_000,
        cached_prompt_tokens=400,
        completion_tokens=200,
        total_tokens=1_200,
        latency_ms=250,
        retry_count=0,
        input_per_million=0.25,
        cached_input_per_million=0.025,
        output_per_million=2.0,
        currency="USD",
        pricing_effective_date="2026-11-18",
    )

    input_cost, output_cost, total_cost = calculate_cost(event)

    assert math.isclose(input_cost, 0.00016)
    assert math.isclose(output_cost, 0.0004)
    assert math.isclose(total_cost, 0.00056)
