using System.Diagnostics;

namespace FoundryFinOps;

public sealed record UsageEvent(
    string Team,
    string Application,
    string CostCenter,
    string Environment,
    string UserId,
    string FoundryResource,
    string Deployment,
    string Model,
    string RequestId,
    int StatusCode,
    bool Success,
    long PromptTokens,
    long CachedPromptTokens,
    long CompletionTokens,
    long TotalTokens,
    double LatencyMs,
    int RetryCount,
    decimal InputPerMillion,
    decimal CachedInputPerMillion,
    decimal OutputPerMillion,
    string Currency,
    string PricingEffectiveDate);

public static class FinOpsRecorder
{
    public const string ActivitySourceName = "Foundry.FinOps";
    private static readonly ActivitySource Source = new(ActivitySourceName);

    public static (decimal Input, decimal Output, decimal Total) CalculateCost(
        UsageEvent usage)
    {
        var uncached = Math.Max(usage.PromptTokens - usage.CachedPromptTokens, 0);
        var input = (uncached * usage.InputPerMillion
            + usage.CachedPromptTokens * usage.CachedInputPerMillion) / 1_000_000m;
        var output = usage.CompletionTokens * usage.OutputPerMillion / 1_000_000m;
        return (input, output, input + output);
    }

    public static void Record(UsageEvent usage)
    {
        var cost = CalculateCost(usage);
        using var activity = Source.StartActivity(
            "ai.finops.usage",
            ActivityKind.Internal);
        if (activity is null)
        {
            return;
        }

        activity.SetTag("schemaVersion", "1.0");
        activity.SetTag("team", usage.Team);
        activity.SetTag("application", usage.Application);
        activity.SetTag("costCenter", usage.CostCenter);
        activity.SetTag("environment", usage.Environment);
        activity.SetTag("userId", usage.UserId);
        activity.SetTag("foundryResource", usage.FoundryResource);
        activity.SetTag("deployment", usage.Deployment);
        activity.SetTag("model", usage.Model);
        activity.SetTag("requestId", usage.RequestId);
        activity.SetTag("traceId", activity.TraceId.ToString());
        activity.SetTag("statusCode", usage.StatusCode);
        activity.SetTag("success", usage.Success);
        activity.SetTag("promptTokens", usage.PromptTokens);
        activity.SetTag("cachedPromptTokens", usage.CachedPromptTokens);
        activity.SetTag("completionTokens", usage.CompletionTokens);
        activity.SetTag("totalTokens", usage.TotalTokens);
        activity.SetTag("latencyMs", usage.LatencyMs);
        activity.SetTag("retryCount", usage.RetryCount);
        activity.SetTag("estimatedInputCost", cost.Input);
        activity.SetTag("estimatedOutputCost", cost.Output);
        activity.SetTag("estimatedTotalCost", cost.Total);
        activity.SetTag("currency", usage.Currency);
        activity.SetTag("pricingEffectiveDate", usage.PricingEffectiveDate);
    }
}
