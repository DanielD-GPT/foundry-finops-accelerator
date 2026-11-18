# Security

## Reporting

Do not open public issues for suspected vulnerabilities. Use the repository
owner's private security reporting channel.

## Data handling

This accelerator records model-usage metadata only. It must not record prompts,
completions, access tokens, authorization headers, or direct personal
identifiers. Use pseudonymous user identifiers and follow your organization's
retention, data-residency, employee-monitoring, and privacy requirements.
Before broad dashboard access, decide whether a privacy impact assessment,
works council consultation, or similar jurisdiction-specific review is
required.

Request-level telemetry should be limited to operators with a legitimate need.
Prefer aggregated dashboards for general business audiences.

## Credentials

Managed identity and Microsoft Entra ID are the supported authentication
methods. Never commit model keys, storage keys, Grafana service-account tokens,
or Application Insights connection strings.

## Reference implementation status

This repository is a reference implementation and has not yet been verified by
a complete live Azure deployment. Local validation and an ARM deployment
preview do not replace post-deployment security testing, RBAC verification,
cost validation, or customer compliance review.
