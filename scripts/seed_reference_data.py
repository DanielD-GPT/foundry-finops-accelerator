import datetime as dt
import json
import pathlib

import requests

import config


def main() -> None:
    root = pathlib.Path(__file__).parent.parent
    pricing = json.loads((root / "config" / "model-pricing.json").read_text())
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    rows = [
        {
            "TimeGenerated": now,
            "Model": model["model"],
            "DeploymentPattern": model["deploymentPattern"],
            "InputPerMillionTokens": model["inputPerMillionTokens"],
            "CachedInputPerMillionTokens": model["cachedInputPerMillionTokens"],
            "OutputPerMillionTokens": model["outputPerMillionTokens"],
            "Currency": pricing["currency"],
            "EffectiveDate": pricing["effectiveDate"],
            "LastVerifiedDate": pricing["lastVerifiedDate"],
            "Source": pricing["source"],
            "Status": model["status"],
        }
        for model in pricing["models"]
    ]
    dcr_name = config.require("PRICING_DCR_NAME")
    dcr = config.dcr(dcr_name)
    url = (
        f"{dcr['endpoint']}/dataCollectionRules/{dcr['immutableId']}"
        "/streams/Custom-Json-AIFinOpsPricing_CL?api-version=2023-01-01"
    )
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {config.token('https://monitor.azure.com')}",
            "Content-Type": "application/json",
        },
        json=rows,
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Pricing ingestion failed: HTTP {response.status_code} {response.text[:500]}"
        )
    print(f"Seeded {len(rows)} pricing rows from {pricing['source']}.")


if __name__ == "__main__":
    main()
