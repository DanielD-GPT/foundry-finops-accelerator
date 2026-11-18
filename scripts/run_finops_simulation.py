import argparse
import concurrent.futures
import json
import logging
import os
import pathlib
import sys
import time
import uuid

import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "instrumentation" / "python"))
from foundry_finops import UsageEvent, emit_usage  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send opt-in direct Foundry traffic and emit privacy-safe FinOps telemetry."
    )
    parser.add_argument("--requests", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-output-tokens", type=int, default=32)
    parser.add_argument("--confirm-live-requests", action="store_true")
    return parser.parse_args()


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def main() -> None:
    args = arguments()
    if not 1 <= args.requests <= 10_000:
        raise ValueError("--requests must be between 1 and 10,000.")
    if not args.confirm_live_requests:
        raise RuntimeError(
            "Live requests can incur model charges. Re-run with --confirm-live-requests."
        )

    configure_azure_monitor(
        connection_string=required("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        logger_name="foundry.finops",
        enable_live_metrics=False,
    )
    logger = logging.getLogger("foundry.finops")
    credential = DefaultAzureCredential()
    endpoint = required("FOUNDRY_ENDPOINT").rstrip("/")
    deployment = os.getenv("FOUNDRY_DEPLOYMENT_NAME", "gpt-5-mini")
    api_version = os.getenv("FOUNDRY_API_VERSION", "2024-10-21")
    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token
    pricing = json.loads(
        (ROOT / "config" / "model-pricing.json").read_text(encoding="utf-8")
    )
    rate = next(
        (item for item in pricing["models"] if item["model"] == deployment),
        pricing["models"][0],
    )

    def invoke(index: int) -> tuple[int, float]:
        started = time.perf_counter()
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": f"Return only the integer {index % 10}.",
                    }
                ],
                "max_tokens": args.max_output_tokens,
            },
            timeout=120,
        )
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.content else {}
        usage = payload.get("usage", {})
        prompt = int(usage.get("prompt_tokens", 0))
        completion = int(usage.get("completion_tokens", 0))
        cached = int(
            usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0
        )
        request_id = response.headers.get("x-request-id", str(uuid.uuid4()))
        trace_id = uuid.uuid4().hex
        emit_usage(
            UsageEvent(
                team=os.getenv("FINOPS_TEAM", "platform-engineering"),
                application=os.getenv("FINOPS_APPLICATION", "simulation-client"),
                cost_center=os.getenv("FINOPS_COST_CENTER", "cc-1000"),
                environment=os.getenv("FINOPS_ENVIRONMENT", "development"),
                user_id=f"simulated-user-{index % 20:02d}",
                foundry_resource=os.getenv("FOUNDRY_RESOURCE_NAME", ""),
                deployment=deployment,
                model=deployment,
                request_id=request_id,
                trace_id=trace_id,
                status_code=response.status_code,
                success=response.ok,
                prompt_tokens=prompt,
                cached_prompt_tokens=cached,
                completion_tokens=completion,
                total_tokens=prompt + completion,
                latency_ms=latency,
                retry_count=0,
                input_per_million=rate["inputPerMillionTokens"],
                cached_input_per_million=rate["cachedInputPerMillionTokens"],
                output_per_million=rate["outputPerMillionTokens"],
                currency=pricing["currency"],
                pricing_effective_date=pricing["effectiveDate"],
            ),
            logger,
        )
        return response.status_code, latency

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, min(args.concurrency, 32))
    ) as executor:
        results = list(executor.map(invoke, range(args.requests)))

    successes = sum(1 for status, _ in results if 200 <= status < 300)
    average_latency = sum(latency for _, latency in results) / len(results)
    print(
        f"Completed {len(results)} live requests: {successes} succeeded, "
        f"{len(results) - successes} failed, average latency {average_latency:.0f} ms."
    )
    if successes != len(results):
        raise RuntimeError("One or more Foundry requests failed.")


if __name__ == "__main__":
    main()
