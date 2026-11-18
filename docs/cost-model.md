# Cost model

## Near-real-time estimate

For each request:

`input = ((prompt - cached) x input_rate + cached x cached_rate) / 1,000,000`

`output = completion x output_rate / 1,000,000`

`estimated_total = input + output`

Rates are stored in `config/model-pricing.json` with currency, effective date, last verified date, source, and verification status. Replace sample values with contract-appropriate rates before production use.

## Actual billed cost

The daily subscription-scope Cost Management export is filtered to the Foundry resource or Cognitive Services meters, aggregated, and ingested into `AIFinOpsCost_CL`. This is the authoritative financial view but arrives later than operational telemetry.

Do not label estimated spend as actual cost. Do not allocate actual resource-level cost to teams unless the customer defines and documents an allocation rule.
