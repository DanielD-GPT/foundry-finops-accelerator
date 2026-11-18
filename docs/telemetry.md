# Telemetry and privacy

`instrumentation/telemetry-contract.md` is the authoritative schema. The solution attributes direct Foundry usage to business dimensions at the application, where the identity and workload context are known.

Use stable pseudonymous user identifiers. Do not emit prompts, completions, access tokens, authorization headers, email addresses, names, or other direct personal identifiers. Keep request and trace IDs so operators can investigate exact calls without storing content.

Applications calculate estimates from response token counts and versioned pricing metadata. This estimate is not an invoice. Azure Cost Management exports provide the authoritative billed amount and can include pricing agreements, rounding, and billing adjustments not represented in local rates.
