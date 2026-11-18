# Microsoft Foundry FinOps Accelerator

Deploy a customer-owned FinOps solution for Microsoft Foundry **without Azure API Management**. Applications call Foundry directly with Microsoft Entra ID or managed identity and emit a privacy-safe `ai.finops.usage` event. Azure Managed Grafana combines that near-real-time telemetry with delayed, authoritative Azure Cost Management exports.

> **Reference implementation.** This accelerator has passed local automated
> tests, Bicep compilation, static RBAC and policy review, Function packaging,
> and an Azure Resource Manager deployment preview. It has **not yet been
> verified through a complete live Azure deployment**. Validate the resulting
> telemetry, cost calculations, role assignments, dashboards, and regional
> service behavior in a non-production subscription before relying on it.

---

## Read this first - what is authoritative and what is estimated

| Dimension | Classification | Source |
|---|---|---|
| Azure resource and meter cost | **Authoritative, delayed** | Azure Cost Management export |
| Request and token counts | **Observed application telemetry** | Instrumented Foundry client |
| Team, application, cost center, and user attribution | **Application supplied** | `ai.finops.usage` properties |
| Near-real-time model cost | **Estimated** | Observed tokens multiplied by customer-verified pricing |
| Actual cost allocated to teams or applications | **Not provided by default** | Requires a customer-defined allocation rule |

Azure Cost Management data can arrive after operational telemetry. The
dashboards intentionally keep **Estimated AI Cost** and **Actual Billed AI
Cost** separate. Do not present token-derived estimates as invoices. The sample
rates in `config/model-pricing.json` are placeholders that require customer
verification against current Azure pricing and contractual terms.

### Verification status

> **Status: not yet verified through a live deployment.** The infrastructure
> targets documented Azure schemas and passed `azd provision --preview`, but no
> resources were provisioned during repository validation. Run the documented
> post-deployment checks before trusting financial or operational output.

### Privacy and governance

This solution can collect per-application and pseudonymous per-user model usage,
token counts, latency, status, and estimated spend. Before sharing dashboards:

- Review retention, access control, data residency, and employee-monitoring
  requirements with your privacy and governance teams.
- Use pseudonymous identifiers rather than names, email addresses, or other
  direct personal identifiers.
- Never emit prompts, completions, access tokens, authorization headers, model
  keys, or other secrets.
- Decide which teams may access request-level detail versus aggregated views.
- Determine whether a privacy impact assessment, works council consultation,
  or similar review is required in applicable jurisdictions.

This project is provided under the MIT License, **as is and without warranty**.
It is not an official Microsoft product, and use of it does not replace
customer security, privacy, compliance, financial, or architectural review.

## What it deploys

- Microsoft Foundry resource and optional `gpt-5-mini` deployment, or an existing Foundry resource
- Log Analytics and Application Insights
- Azure Managed Grafana with three customer-facing dashboards
- Storage for Cost Management exports and Function deployment artifacts
- Flex Consumption Function that normalizes billing exports into `AIFinOpsCost_CL`
- Direct data collection rules for pricing and actual cost
- Least-privilege managed identities and role assignments

No API Management resource, policy, key, or dependency is used.

## Dashboards

1. **Executive Overview** - estimated cost, actual billed cost, budget usage, requests, tokens, latency, business allocation, and freshness
2. **Consumption and Efficiency** - unit economics, model utilization, success rate, failures, cost centers, and applications
3. **Detailed AI Usage** - request-level attribution with exact trace drill-through into Azure Monitor

Estimated token cost and actual billed cost are intentionally presented as separate values. Model pricing in `config/model-pricing.json` is sample data and must be verified before production use.

## Prerequisites

- Azure CLI, Azure Developer CLI (`azd`), PowerShell 7, Python 3.11+
- Node.js 20+ and .NET 8 SDK to validate all instrumentation samples
- Owner or User Access Administrator plus Contributor at the deployment scope
- A region with Microsoft Foundry model capacity and Azure Managed Grafana availability

## Deploy

```powershell
az login
azd auth login
azd init
azd env set AZURE_LOCATION northcentralus
azd env set GRAFANA_LOCATION centralus
azd env set ENVIRONMENT_TIER development
azd env set DEPLOY_SAMPLE_MODEL false
.\scripts\deploy.ps1
```

To reuse Foundry:

```powershell
azd env set EXISTING_FOUNDRY_NAME <name>
azd env set EXISTING_FOUNDRY_RESOURCE_GROUP <resource-group>
```

To create Foundry and a sample deployment:

```powershell
azd env set DEPLOY_SAMPLE_MODEL true
```

The script validates locally, provisions infrastructure, deploys the Function, seeds versioned pricing, imports dashboards, and prints the Managed Grafana endpoint.

## Instrument applications

Use the canonical contract in `instrumentation/telemetry-contract.md` and one of:

- `instrumentation/python`
- `instrumentation/dotnet`
- `instrumentation/typescript`

Applications must populate team, application, cost center, environment, pseudonymous user ID, model/deployment, token counts, request status, latency, request ID, and trace ID. Never emit prompts, completions, tokens, authorization headers, or direct personal identifiers.

## Optional smoke traffic

Copy `.env.example` to `.env`, set `FOUNDRY_ENDPOINT` and the generated Application Insights connection string, then explicitly approve billable requests:

```powershell
python .\scripts\run_finops_simulation.py --requests 10 --concurrency 2 --confirm-live-requests
```

The simulator caps each run at 10,000 requests and does nothing without `--confirm-live-requests`.

## Validate and operate

```powershell
pip install -r requirements.txt
.\scripts\validate.ps1
python .\scripts\validate_dashboard_queries.py
```

The live query validator requires a deployed environment and Azure login. Cost Management exports normally appear with billing latency; an empty Actual Billed Cost panel immediately after deployment is expected.

## Remove

```powershell
.\scripts\teardown.ps1 -EnvironmentName <azd-environment>
```

The command displays the exact environment resources and requires the environment name as confirmation.

## Cost controls

The baseline development footprint is dominated by Managed Grafana (approximately USD 63/month for two Standard Units, plus active-user charges). Low-volume development is approximately USD 90-110/month before model usage. Actual prices vary by region and agreement. Use production retention/ZRS only when required and remove unused environments.

See `docs/deployment.md`, `docs/operations.md`, `docs/telemetry.md`, and `docs/cost-model.md` for detailed guidance.
