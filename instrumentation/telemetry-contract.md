# AI FinOps Telemetry Contract

Every direct Microsoft Foundry client emits an informational log named
`ai.finops.usage`. The log must not contain prompt or completion text.

## Required properties

| Property | Type | Description |
|---|---|---|
| `schemaVersion` | string | Contract version; currently `1.0` |
| `team` | string | Stable team identifier |
| `application` | string | Calling application |
| `costCenter` | string | Financial allocation identifier |
| `environment` | string | `development`, `test`, or `production` |
| `userId` | string | Pseudonymous user identifier |
| `foundryResource` | string | Foundry resource name |
| `deployment` | string | Model deployment |
| `model` | string | Model family |
| `requestId` | string | Model request identifier |
| `traceId` | string | Distributed trace identifier |
| `statusCode` | integer | HTTP status |
| `success` | boolean | Request outcome |
| `promptTokens` | integer | Input tokens |
| `cachedPromptTokens` | integer | Cached input tokens |
| `completionTokens` | integer | Output tokens |
| `totalTokens` | integer | Total tokens |
| `latencyMs` | real | End-to-end client latency |
| `retryCount` | integer | Client retries |
| `estimatedInputCost` | real | Token-derived estimate |
| `estimatedOutputCost` | real | Token-derived estimate |
| `estimatedTotalCost` | real | Token-derived estimate |
| `currency` | string | Pricing currency |
| `pricingEffectiveDate` | string | Pricing table effective date |

## Privacy

- Never emit prompt or completion content.
- Never emit access tokens, API keys, cookies, or authorization headers.
- Pseudonymize user identifiers before calling the recorder.
- Use a stable shared schema across every application.
