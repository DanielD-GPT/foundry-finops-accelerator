import csv
import datetime as dt
import gzip
import io
import json
import logging
import os
from collections import defaultdict

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()


def _credential() -> DefaultAzureCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    return DefaultAzureCredential(managed_identity_client_id=client_id)


def _first(row: dict[str, str], *names: str) -> str:
    lower = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return value
    return ""


def _parse_cost_rows(content: bytes, blob_name: str) -> list[dict]:
    if blob_name.lower().endswith(".gz"):
        content = gzip.decompress(content)
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    foundry_resource_id = os.environ["FOUNDRY_RESOURCE_ID"].lower().rstrip("/")
    currency_default = os.getenv("COST_CURRENCY", "USD")
    aggregates: dict[tuple[str, ...], float] = defaultdict(float)

    for row in reader:
        resource_id = _first(row, "ResourceId", "Resource ID").lower().rstrip("/")
        service = _first(row, "ServiceName", "ConsumedService", "Service name")
        if resource_id != foundry_resource_id and "cognitive" not in service.lower():
            continue

        usage_date = _first(row, "Date", "UsageDate", "Usage date")
        meter = _first(row, "MeterName", "Meter", "Meter name")
        pricing_model = _first(row, "PricingModel", "Pricing model")
        resource_name = _first(row, "ResourceName", "Resource name")
        currency = _first(row, "BillingCurrency", "Currency") or currency_default
        tags = _first(row, "Tags")
        cost_text = _first(
            row,
            "CostInBillingCurrency",
            "PreTaxCost",
            "Cost",
        )
        try:
            cost = float(cost_text)
        except (TypeError, ValueError):
            logging.warning("Skipping cost row with invalid cost value: %r", cost_text)
            continue

        key = (
            usage_date,
            resource_id,
            resource_name,
            service,
            meter,
            pricing_model,
            currency,
            tags,
        )
        aggregates[key] += cost

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    return [
        {
            "TimeGenerated": now,
            "UsageDate": key[0],
            "SubscriptionId": os.environ["AZURE_SUBSCRIPTION_ID"],
            "ResourceGroup": os.environ["FOUNDRY_RESOURCE_GROUP"],
            "ResourceId": key[1],
            "ResourceName": key[2],
            "ServiceName": key[3],
            "MeterName": key[4],
            "PricingModel": key[5],
            "ActualCost": cost,
            "Currency": key[6],
            "Tags": key[7],
            "SourceBlob": blob_name,
            "IngestedAt": now,
        }
        for key, cost in aggregates.items()
    ]


def _load_state(container) -> set[str]:
    state_blob = container.get_blob_client("state/processed.json")
    try:
        payload = json.loads(state_blob.download_blob().readall())
        return set(payload.get("processed", []))
    except Exception as exc:
        if getattr(exc, "status_code", None) == 404:
            return set()
        raise


def _save_state(container, processed: set[str]) -> None:
    state_blob = container.get_blob_client("state/processed.json")
    state_blob.upload_blob(
        json.dumps({"processed": sorted(processed)}, separators=(",", ":")),
        overwrite=True,
    )


@app.timer_trigger(
    schedule="%COST_NORMALIZER_SCHEDULE%",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def normalize_cost_export(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.warning("Cost normalization timer is running late.")

    credential = _credential()
    blob_service = BlobServiceClient(
        account_url=os.environ["COST_EXPORT_STORAGE_URL"],
        credential=credential,
    )
    container = blob_service.get_container_client(
        os.getenv("COST_EXPORT_CONTAINER", "cost-exports")
    )
    processed = _load_state(container)
    candidates = [
        blob
        for blob in container.list_blobs(name_starts_with="exports/")
        if blob.name.lower().endswith((".csv", ".csv.gz"))
        and blob.name not in processed
    ]
    candidates.sort(key=lambda blob: blob.last_modified)

    ingestion = LogsIngestionClient(
        endpoint=os.environ["ACTUAL_COST_DCR_ENDPOINT"],
        credential=credential,
    )
    uploaded = 0
    for blob in candidates:
        content = container.download_blob(blob.name).readall()
        rows = _parse_cost_rows(content, blob.name)
        if rows:
            ingestion.upload(
                rule_id=os.environ["ACTUAL_COST_DCR_IMMUTABLE_ID"],
                stream_name=os.environ["ACTUAL_COST_DCR_STREAM"],
                logs=rows,
            )
            uploaded += len(rows)
        processed.add(blob.name)

    if candidates:
        _save_state(container, processed)
    logging.info(
        "Normalized %d export files into %d actual-cost rows.",
        len(candidates),
        uploaded,
    )
