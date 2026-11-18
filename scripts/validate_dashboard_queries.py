import json
import pathlib

import requests

import config


def materialize(query: str) -> str:
    return (
        query.replace(
            "$__timeFilter(TimeGenerated)",
            "TimeGenerated between (ago(24h) .. now())",
        )
        .replace('"$team"', '"All"')
        .replace('"$application"', '"All"')
        .replace('"$model"', '"All"')
    )


def main() -> None:
    root = pathlib.Path(__file__).parent.parent
    endpoint = (
        f"https://api.loganalytics.io/v1/workspaces/{config.workspace_guid()}/query"
    )
    failures = []
    count = 0
    for path in sorted((root / "dashboards").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for panel in document["dashboard"]["panels"]:
            for panel_target in panel.get("targets", []):
                query = panel_target.get("azureLogAnalytics", {}).get("query")
                if not query:
                    continue
                count += 1
                response = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {config.token('https://api.loganalytics.io')}",
                        "Content-Type": "application/json",
                    },
                    json={"query": materialize(query)},
                    timeout=120,
                )
                if response.status_code >= 400:
                    failures.append(
                        f"{path.name} / {panel['title']}: {response.text[:500]}"
                    )
                    print(f"FAIL {path.name} / {panel['title']}")
                else:
                    print(f"OK   {path.name} / {panel['title']}")

    if failures:
        raise RuntimeError("\n".join(failures))
    print(f"Validated {count} live dashboard queries.")


if __name__ == "__main__":
    main()
