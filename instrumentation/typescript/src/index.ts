import { trace } from "@opentelemetry/api";

export interface UsageEvent {
  team: string;
  application: string;
  costCenter: string;
  environment: string;
  userId: string;
  foundryResource: string;
  deployment: string;
  model: string;
  requestId: string;
  statusCode: number;
  success: boolean;
  promptTokens: number;
  cachedPromptTokens: number;
  completionTokens: number;
  totalTokens: number;
  latencyMs: number;
  retryCount: number;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  outputPerMillion: number;
  currency: string;
  pricingEffectiveDate: string;
}

export function calculateCost(event: UsageEvent) {
  const uncached = Math.max(event.promptTokens - event.cachedPromptTokens, 0);
  const input =
    (uncached * event.inputPerMillion +
      event.cachedPromptTokens * event.cachedInputPerMillion) /
    1_000_000;
  const output =
    (event.completionTokens * event.outputPerMillion) / 1_000_000;
  return { input, output, total: input + output };
}

export function recordUsage(event: UsageEvent): void {
  const tracer = trace.getTracer("foundry.finops", "1.0.0");
  const span = tracer.startSpan("ai.finops.usage");
  const cost = calculateCost(event);
  span.setAttributes({
    schemaVersion: "1.0",
    ...event,
    traceId: span.spanContext().traceId,
    estimatedInputCost: cost.input,
    estimatedOutputCost: cost.output,
    estimatedTotalCost: cost.total
  });
  span.end();
}
