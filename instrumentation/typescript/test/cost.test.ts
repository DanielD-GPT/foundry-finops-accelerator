import assert from "node:assert/strict";
import test from "node:test";
import { calculateCost, type UsageEvent } from "../src/index.js";

test("calculateCost accounts for cached input", () => {
  const usage: UsageEvent = {
    team: "platform",
    application: "sample",
    costCenter: "cc-1000",
    environment: "test",
    userId: "user-001",
    foundryResource: "foundry",
    deployment: "gpt-5-mini",
    model: "gpt-5-mini",
    requestId: "request-1",
    statusCode: 200,
    success: true,
    promptTokens: 1000,
    cachedPromptTokens: 400,
    completionTokens: 200,
    totalTokens: 1200,
    latencyMs: 250,
    retryCount: 0,
    inputPerMillion: 0.25,
    cachedInputPerMillion: 0.025,
    outputPerMillion: 2,
    currency: "USD",
    pricingEffectiveDate: "2026-11-18"
  };

  const cost = calculateCost(usage);

  assert.ok(Math.abs(cost.input - 0.00016) < 1e-12);
  assert.ok(Math.abs(cost.output - 0.0004) < 1e-12);
  assert.ok(Math.abs(cost.total - 0.00056) < 1e-12);
});
