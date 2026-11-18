import functools
import json
import os
import pathlib
import subprocess
import sys

import requests

ARM = "https://management.azure.com"


def _load_dotenv() -> None:
    for candidate in (
        pathlib.Path(".env"),
        pathlib.Path(__file__).parent.parent / ".env",
    ):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
        return


_load_dotenv()


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(
            f"ERROR: {name} is required. Run 'azd env get-values' or set it in .env."
        )
    return value


SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "")
RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "")
LOCATION = os.getenv("AZURE_LOCATION", "")
LAW_NAME = os.getenv("LOG_ANALYTICS_WORKSPACE_NAME", "")
APPINSIGHTS_NAME = os.getenv("APPLICATION_INSIGHTS_NAME", "")
GRAFANA_NAME = os.getenv("GRAFANA_NAME", "")
FOUNDRY_NAME = os.getenv("FOUNDRY_RESOURCE_NAME", "")
FOUNDRY_RESOURCE_GROUP = os.getenv("FOUNDRY_RESOURCE_GROUP", RESOURCE_GROUP)
FOUNDRY_DEPLOYMENT = os.getenv("FOUNDRY_DEPLOYMENT_NAME", "gpt-5-mini")


@functools.lru_cache(maxsize=8)
def token(resource: str = ARM) -> str:
    try:
        return subprocess.check_output(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                resource,
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            shell=(os.name == "nt"),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        sys.exit("ERROR: unable to acquire an Azure token. Run 'az login'.")


def arm_get(path: str, api_version: str) -> dict:
    response = requests.get(
        f"{ARM}{path}",
        headers={"Authorization": f"Bearer {token()}"},
        params={"api-version": api_version},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def resource_id(provider: str, name: str, resource_group: str | None = None) -> str:
    return (
        f"/subscriptions/{require('AZURE_SUBSCRIPTION_ID')}"
        f"/resourceGroups/{resource_group or require('AZURE_RESOURCE_GROUP')}"
        f"/providers/{provider}/{name}"
    )


def workspace_resource_id() -> str:
    return resource_id(
        "Microsoft.OperationalInsights/workspaces",
        require("LOG_ANALYTICS_WORKSPACE_NAME"),
    )


def workspace_guid() -> str:
    return arm_get(workspace_resource_id(), "2023-09-01")["properties"]["customerId"]


def grafana_endpoint() -> str:
    data = arm_get(
        resource_id("Microsoft.Dashboard/grafana", require("GRAFANA_NAME")),
        "2023-09-01",
    )
    return data["properties"]["endpoint"]


def dcr(name: str) -> dict:
    data = arm_get(
        resource_id("Microsoft.Insights/dataCollectionRules", name),
        "2023-03-11",
    )
    properties = data["properties"]
    return {
        "immutableId": properties["immutableId"],
        "endpoint": properties["endpoints"]["logsIngestion"],
    }


def load_azd_environment() -> None:
    result = subprocess.run(
        ["azd", "env", "get-values"],
        shell=(os.name == "nt"),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip("\""))


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "subscription": SUBSCRIPTION_ID,
                "resourceGroup": RESOURCE_GROUP,
                "workspace": LAW_NAME,
                "grafana": GRAFANA_NAME,
                "foundry": FOUNDRY_NAME,
            },
            indent=2,
        )
    )
