# Operations guide

## Data freshness

Operational telemetry normally reaches Application Insights within minutes. Azure Cost Management data is authoritative but delayed; daily export arrival depends on the billing pipeline.

## Routine checks

1. Confirm the Executive Overview freshness panel has recent operational telemetry.
2. Confirm the `cost-exports` container receives daily files.
3. Inspect the cost-normalizer Function invocation and failure metrics.
4. Compare estimated and actual cost only across equivalent periods.
5. Review pricing metadata before interpreting estimates.

## Dashboard maintenance

Run `python scripts/build_dashboards.py` after changing the generator. Run `python scripts/import_dashboards.py` to overwrite dashboards by stable UID. `dashboard-import-results.json` contains the deployed URLs and is excluded from source control.

## Troubleshooting

- No operational data: verify `APPLICATIONINSIGHTS_CONNECTION_STRING`, logger configuration, and the exact `ai.finops.usage` event name.
- No billed data: verify export delivery first; a delay immediately after deployment is expected.
- Dashboard access denied: verify the user has Grafana Viewer/Admin and the Grafana managed identity has Monitoring Reader and Log Analytics Reader.
- Function ingestion denied: verify storage and DCR role propagation, then retry after several minutes.
