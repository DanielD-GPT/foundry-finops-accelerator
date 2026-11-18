using FoundryFinOps;
using Xunit;

namespace FoundryFinOps.Tests;

public class FinOpsRecorderTests
{
    [Fact]
    public void CalculateCostAccountsForCachedInput()
    {
        var usage = new UsageEvent(
            "platform", "sample", "cc-1000", "test", "user-001",
            "foundry", "gpt-5-mini", "gpt-5-mini", "request-1", 200, true,
            1000, 400, 200, 1200, 250, 0,
            0.25m, 0.025m, 2.0m, "USD", "2026-11-18");

        var cost = FinOpsRecorder.CalculateCost(usage);

        Assert.Equal(0.00016m, cost.Input);
        Assert.Equal(0.0004m, cost.Output);
        Assert.Equal(0.00056m, cost.Total);
    }
}
