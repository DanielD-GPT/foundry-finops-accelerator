import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PLAIN_LANGUAGE_FORBIDDEN = (
    "AppTraces",
    "AIFinOpsCost_CL",
    "AIFinOpsPricing_CL",
    "Properties",
)


def main() -> None:
    errors = []
    for path in sorted((ROOT / "dashboards").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        dashboard = document.get("dashboard", document)
        if not dashboard.get("uid"):
            errors.append(f"{path.name}: dashboard UID is missing")
        for panel in dashboard.get("panels", []):
            title = panel.get("title", "")
            description = panel.get("description", "")
            if not description:
                errors.append(f"{path.name}: {title} has no description")
            if any(value in title for value in PLAIN_LANGUAGE_FORBIDDEN):
                errors.append(f"{path.name}: technical panel title '{title}'")
            for target in panel.get("targets", []):
                query = target.get("azureLogAnalytics", {}).get("query", "")
                if query and "$__timeFilter(TimeGenerated)" not in query and (
                    "startofmonth" not in query
                ):
                    errors.append(f"{path.name}: {title} ignores the time picker")

    pricing = json.loads(
        (ROOT / "config" / "model-pricing.json").read_text(encoding="utf-8")
    )
    for key in ("currency", "effectiveDate", "lastVerifiedDate", "source"):
        if not pricing.get(key):
            errors.append(f"model-pricing.json: {key} is required")

    for path in ROOT.rglob("*"):
        excluded = {"node_modules", "dist", "bin", "obj", ".git", ".pytest_cache", "__pycache__"}
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".ps1", ".json", ".md", ".bicep", ".yaml", ".yml", ".ts", ".cs"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?i)(api[_-]?key|client[_-]?secret)\s*[:=]\s*['\"][^$<{][^'\"]{8,}", text):
            errors.append(f"{path.relative_to(ROOT)}: possible committed secret")

    if errors:
        raise RuntimeError("\n".join(errors))
    print("Dashboard UX, pricing metadata, and secret checks passed.")


if __name__ == "__main__":
    main()
