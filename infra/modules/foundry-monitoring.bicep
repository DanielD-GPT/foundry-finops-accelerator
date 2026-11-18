param foundryName string
param workspaceResourceId string

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryName
}

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: foundry
  name: 'foundry-finops'
  properties: {
    workspaceId: workspaceResourceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}
