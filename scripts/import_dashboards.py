import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse

import config

DASHBOARD_FILES = (
    "ai-finops-executive-overview.json",
    "ai-consumption-efficiency.json",
    "ai-usage-detail.json",
)


def main() -> None:
    root = pathlib.Path(__file__).parent.parent
    subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).with_name("build_dashboards.py"))],
        check=True,
    )
    workspace_id = config.workspace_resource_id()
    replacements = {
        "${LOG_ANALYTICS_RESOURCE_ID}": workspace_id,
        "${LOG_ANALYTICS_RESOURCE_ID_ENCODED}": urllib.parse.quote(
            workspace_id, safe=""
        ),
    }
    results = []
    endpoint = config.grafana_endpoint().rstrip("/")

    for name in DASHBOARD_FILES:
        content = (root / "dashboards" / name).read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        if "${LOG_ANALYTICS_RESOURCE_ID" in content:
            raise RuntimeError(f"{name} contains unresolved resource placeholders.")
        json.loads(content)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as file:
            file.write(content)
            temp_path = pathlib.Path(file.name)
        try:
            command = [
                "az",
                "grafana",
                "dashboard",
                "create",
                "--resource-group",
                config.require("AZURE_RESOURCE_GROUP"),
                "--name",
                config.require("GRAFANA_NAME"),
                "--definition",
                str(temp_path),
                "--overwrite",
                "true",
                "--query",
                "{uid:uid,url:url}",
                "-o",
                "json",
            ]
            completed = subprocess.run(
                command,
                shell=(sys.platform == "win32"),
                capture_output=True,
                text=True,
            )
            if completed.returncode:
                raise RuntimeError(
                    f"Dashboard import failed for {name}: {completed.stderr.strip()}"
                )
            result = json.loads(completed.stdout)
            result["name"] = name
            result["absoluteUrl"] = f"{endpoint}{result['url']}"
            results.append(result)
            print(f"OK {name}: {result['absoluteUrl']}")
        finally:
            temp_path.unlink(missing_ok=True)

    (root / "dashboard-import-results.json").write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
