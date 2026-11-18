import json
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
DASHBOARDS = ROOT / "dashboards"
DATASOURCE = {
    "type": "grafana-azure-monitor-datasource",
    "uid": "azure-monitor-oob",
}

USAGE = """let usage = AppTraces
| where $__timeFilter(TimeGenerated)
| where Message == "ai.finops.usage"
| extend Team=tostring(Properties["team"]),
         Application=tostring(Properties["application"]),
         CostCenter=tostring(Properties["costCenter"]),
         Environment=tostring(Properties["environment"]),
         UserId=tostring(Properties["userId"]),
         FoundryResource=tostring(Properties["foundryResource"]),
         Deployment=tostring(Properties["deployment"]),
         Model=tostring(Properties["model"]),
         RequestId=tostring(Properties["requestId"]),
         TraceId=tostring(Properties["traceId"]),
         StatusCode=toint(Properties["statusCode"]),
         Success=tobool(Properties["success"]),
         PromptTokens=tolong(Properties["promptTokens"]),
         CachedPromptTokens=tolong(Properties["cachedPromptTokens"]),
         CompletionTokens=tolong(Properties["completionTokens"]),
         TotalTokens=tolong(Properties["totalTokens"]),
         LatencyMs=todouble(Properties["latencyMs"]),
         EstimatedCost=todouble(Properties["estimatedTotalCost"]),
         Currency=tostring(Properties["currency"]),
         PricingEffectiveDate=tostring(Properties["pricingEffectiveDate"])
| where ("$team" == "All" or Team == "$team")
  and ("$application" == "All" or Application == "$application")
  and ("$model" == "All" or Model == "$model");
"""


def target(query: str, result_format: str = "table") -> list[dict]:
    return [
        {
            "refId": "A",
            "queryType": "Azure Log Analytics",
            "azureLogAnalytics": {
                "resources": ["${LOG_ANALYTICS_RESOURCE_ID}"],
                "resultFormat": result_format,
                "query": query,
            },
        }
    ]


def panel(
    panel_id: int,
    title: str,
    description: str,
    panel_type: str,
    query: str,
    grid: tuple[int, int, int, int],
    unit: str = "short",
    decimals: int | None = None,
    options: dict | None = None,
) -> dict:
    x, y, width, height = grid
    defaults = {
        "unit": unit,
        "noValue": "No traffic in this period",
        "color": {"mode": "palette-classic"},
    }
    if decimals is not None:
        defaults["decimals"] = decimals
    return {
        "id": panel_id,
        "title": title,
        "description": description,
        "type": panel_type,
        "datasource": DATASOURCE,
        "gridPos": {"x": x, "y": y, "w": width, "h": height},
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": options or {},
        "targets": target(query, "time_series" if panel_type == "timeseries" else "table"),
    }


def dashboard(title: str, uid: str, panels: list[dict], tags: list[str]) -> dict:
    return {
        "dashboard": {
            "id": None,
            "uid": uid,
            "title": title,
            "description": "Microsoft Foundry FinOps without API Management.",
            "tags": ["foundry", "finops", "azure-monitor", *tags],
            "timezone": "browser",
            "schemaVersion": 39,
            "version": 1,
            "refresh": "1m",
            "time": {"from": "now-24h", "to": "now"},
            "templating": {
                "list": [
                    {
                        "name": name,
                        "label": label,
                        "type": "custom",
                        "query": "All",
                        "current": {"text": "All", "value": "All"},
                        "options": [{"text": "All", "value": "All", "selected": True}],
                    }
                    for name, label in (
                        ("team", "Team"),
                        ("application", "Application"),
                        ("model", "Model"),
                    )
                ]
            },
            "panels": panels,
        },
        "overwrite": True,
    }


def executive() -> dict:
    panels = [
        panel(1, "Estimated AI Cost", "Near-real-time token-derived estimate for the selected period.", "stat",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost)", (0, 0, 4, 4), "currencyUSD", 4),
        panel(2, "Actual Billed AI Cost", "Authoritative Cost Management data; normal Azure billing latency applies.", "stat",
              'AIFinOpsCost_CL | where $__timeFilter(TimeGenerated) | summarize ActualCost=sum(ActualCost)',
              (4, 0, 4, 4), "currencyUSD", 2),
        panel(3, "Monthly Budget Used", "Estimated spend divided by the configured monthly dashboard budget.", "gauge",
              USAGE + 'usage | summarize EstimatedCost=sum(EstimatedCost) | extend Budget=1000.0 | project PercentUsed=100.0*EstimatedCost/Budget',
              (8, 0, 4, 4), "percent", 1,
              {"showThresholdLabels": True, "showThresholdMarkers": True}),
        panel(4, "Total Model Requests", "Instrumented direct-to-Foundry requests.", "stat",
              USAGE + "usage | summarize Requests=count()", (12, 0, 4, 4), "short", 0),
        panel(5, "Total Tokens Consumed", "Prompt and completion tokens reported by model responses.", "stat",
              USAGE + "usage | summarize Tokens=sum(TotalTokens)", (16, 0, 4, 4), "short", 0),
        panel(6, "Average Model Response Time", "End-to-end response time measured by calling applications.", "stat",
              USAGE + "usage | summarize AverageLatency=avg(LatencyMs)", (20, 0, 4, 4), "ms", 0),
        panel(7, "AI Cost Over Time", "Estimated cost trend from token telemetry.", "timeseries",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by bin(TimeGenerated, 15m)",
              (0, 4, 12, 8), "currencyUSD", 4),
        panel(8, "Token Consumption Over Time", "Total token consumption over time.", "timeseries",
              USAGE + "usage | summarize Tokens=sum(TotalTokens) by bin(TimeGenerated, 15m)",
              (12, 4, 12, 8), "short", 0),
        panel(9, "Cost by Model", "Compare estimated cost across model families.", "barchart",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by Model | order by EstimatedCost desc",
              (0, 12, 8, 8), "currencyUSD", 4),
        panel(10, "Cost by Team", "Allocate estimated AI cost to business teams.", "barchart",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by Team | order by EstimatedCost desc",
              (8, 12, 8, 8), "currencyUSD", 4),
        panel(11, "Cost by Application", "Identify applications driving AI spend.", "barchart",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by Application | order by EstimatedCost desc",
              (16, 12, 8, 8), "currencyUSD", 4),
        panel(12, "Data Freshness", "Shows the newest operational and authoritative cost records.", "table",
              'let usage=AppTraces | where $__timeFilter(TimeGenerated) | where Message=="ai.finops.usage" | summarize LastOperational=max(TimeGenerated); let cost=AIFinOpsCost_CL | where $__timeFilter(TimeGenerated) | summarize LastBilled=max(TimeGenerated); usage | extend Key=1 | join kind=fullouter (cost | extend Key=1) on Key | project LastOperational, LastBilled, BillingNote="Actual billing data is delayed by Azure Cost Management."',
              (0, 20, 24, 5)),
    ]
    return dashboard("Microsoft Foundry FinOps - Executive Overview", "foundry-finops-overview", panels, ["executive"])


def efficiency() -> dict:
    panels = [
        panel(1, "Requests by Model", "Request volume by model.", "barchart",
              USAGE + "usage | summarize Requests=count() by Model | order by Requests desc", (0, 0, 8, 8)),
        panel(2, "Tokens by Model", "Token consumption by model.", "barchart",
              USAGE + "usage | summarize Tokens=sum(TotalTokens) by Model | order by Tokens desc", (8, 0, 8, 8)),
        panel(3, "Tokens per Request", "Average token intensity by model.", "barchart",
              USAGE + "usage | summarize TokensPerRequest=avg(todouble(TotalTokens)) by Model | order by TokensPerRequest desc",
              (16, 0, 8, 8), "short", 1),
        panel(4, "Cost per 1,000 Requests", "Estimated unit cost normalized to 1,000 requests.", "barchart",
              USAGE + "usage | summarize Cost=sum(EstimatedCost), Requests=count() by Model | extend CostPer1000=1000.0*Cost/Requests | order by CostPer1000 desc",
              (0, 8, 8, 8), "currencyUSD", 3),
        panel(5, "Average Response Time by Model", "Client-observed response time.", "barchart",
              USAGE + "usage | summarize AverageLatency=avg(LatencyMs) by Model | order by AverageLatency desc",
              (8, 8, 8, 8), "ms", 0),
        panel(6, "Request Success Rate", "Percentage of successful instrumented calls.", "gauge",
              USAGE + "usage | summarize Total=count(), Successful=countif(Success) | project SuccessRate=100.0*Successful/Total",
              (16, 8, 8, 8), "percent", 1),
        panel(7, "Failed Requests", "Failed calls grouped by model and status.", "table",
              USAGE + "usage | where not(Success) | summarize Failures=count() by Model, StatusCode | order by Failures desc",
              (0, 16, 8, 8)),
        panel(8, "Top Cost Centers", "Highest estimated spend by cost center.", "barchart",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by CostCenter | top 10 by EstimatedCost desc",
              (8, 16, 8, 8), "currencyUSD", 4),
        panel(9, "Top Applications", "Applications with the highest estimated spend.", "barchart",
              USAGE + "usage | summarize EstimatedCost=sum(EstimatedCost) by Application | top 10 by EstimatedCost desc",
              (16, 16, 8, 8), "currencyUSD", 4),
    ]
    return dashboard("Microsoft Foundry FinOps - Consumption and Efficiency", "foundry-finops-efficiency", panels, ["efficiency"])


def detail() -> dict:
    query = USAGE + """usage
| project TimeGenerated, Team, Application, CostCenter, UserId, Model, Deployment,
          PromptTokens, CachedPromptTokens, CompletionTokens, TotalTokens,
          EstimatedCost, Currency, LatencyMs, StatusCode, RequestId, TraceId,
          OperationId
| order by TimeGenerated desc
| take 1000"""
    table = panel(
        1,
        "Detailed AI Usage",
        "Searchable request-level model usage with exact Azure Monitor drill-through.",
        "table",
        query,
        (0, 0, 24, 20),
        "short",
    )
    table["fieldConfig"]["overrides"] = [
        {
            "matcher": {"id": "byName", "options": "EstimatedCost"},
            "properties": [{"id": "unit", "value": "currencyUSD"}, {"id": "decimals", "value": 5}],
        },
        {
            "matcher": {"id": "byName", "options": "LatencyMs"},
            "properties": [{"id": "unit", "value": "ms"}],
        },
        {
            "matcher": {"id": "byName", "options": "TraceId"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Open exact trace in Azure Monitor",
                            "targetBlank": True,
                            "url": "https://portal.azure.com/#blade/Microsoft_Azure_Monitoring_Logs/LogsBlade/resourceId/${LOG_ANALYTICS_RESOURCE_ID_ENCODED}/source/LogsBlade.AnalyticsShareLinkToQuery/query/AppTraces%20%7C%20where%20tostring(Properties%5B%22traceId%22%5D)%20%3D%3D%20%22${__value.raw}%22%20%7C%20order%20by%20TimeGenerated%20desc/isQueryBase64Compressed/false/timespan/PT24H",
                        }
                    ],
                }
            ],
        },
    ]
    return dashboard("Microsoft Foundry FinOps - Detailed AI Usage", "foundry-finops-detail", [table], ["detail"])


def main() -> None:
    DASHBOARDS.mkdir(parents=True, exist_ok=True)
    outputs = {
        "ai-finops-executive-overview.json": executive(),
        "ai-consumption-efficiency.json": efficiency(),
        "ai-usage-detail.json": detail(),
    }
    for name, content in outputs.items():
        (DASHBOARDS / name).write_text(
            json.dumps(content, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Generated {name}")


if __name__ == "__main__":
    main()
