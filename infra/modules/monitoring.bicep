param location string
param resourceToken string
param retentionDays int = 30
param tags object = {}

var logAnalyticsName = 'log-finops-${resourceToken}'
var applicationInsightsName = 'appi-finops-${resourceToken}'
var pricingTableName = 'AIFinOpsPricing_CL'
var actualCostTableName = 'AIFinOpsCost_CL'
var pricingStream = 'Custom-Json-${pricingTableName}'
var actualCostStream = 'Custom-Json-${actualCostTableName}'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: retentionDays
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
    IngestionMode: 'LogAnalytics'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource pricingTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  parent: logAnalytics
  name: pricingTableName
  properties: {
    plan: 'Analytics'
    retentionInDays: retentionDays
    totalRetentionInDays: 730
    schema: {
      name: pricingTableName
      description: 'Versioned model prices used for near-real-time AI cost estimates.'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'Model', type: 'string' }
        { name: 'DeploymentPattern', type: 'string' }
        { name: 'InputPerMillionTokens', type: 'real' }
        { name: 'CachedInputPerMillionTokens', type: 'real' }
        { name: 'OutputPerMillionTokens', type: 'real' }
        { name: 'Currency', type: 'string' }
        { name: 'EffectiveDate', type: 'string' }
        { name: 'LastVerifiedDate', type: 'string' }
        { name: 'Source', type: 'string' }
        { name: 'Status', type: 'string' }
      ]
    }
  }
}

resource actualCostTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  parent: logAnalytics
  name: actualCostTableName
  properties: {
    plan: 'Analytics'
    retentionInDays: retentionDays
    totalRetentionInDays: 730
    schema: {
      name: actualCostTableName
      description: 'Normalized authoritative Azure Cost Management rows for Foundry.'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'UsageDate', type: 'string' }
        { name: 'SubscriptionId', type: 'string' }
        { name: 'ResourceGroup', type: 'string' }
        { name: 'ResourceId', type: 'string' }
        { name: 'ResourceName', type: 'string' }
        { name: 'ServiceName', type: 'string' }
        { name: 'MeterName', type: 'string' }
        { name: 'PricingModel', type: 'string' }
        { name: 'ActualCost', type: 'real' }
        { name: 'Currency', type: 'string' }
        { name: 'Tags', type: 'string' }
        { name: 'SourceBlob', type: 'string' }
        { name: 'IngestedAt', type: 'datetime' }
      ]
    }
  }
}

resource pricingDcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: 'dcr-finops-pricing-${resourceToken}'
  location: location
  kind: 'Direct'
  tags: tags
  properties: {
    streamDeclarations: {
      '${pricingStream}': {
        columns: pricingTable.properties.schema.columns
      }
    }
    destinations: {
      logAnalytics: [
        {
          name: 'workspace'
          workspaceResourceId: logAnalytics.id
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          pricingStream
        ]
        destinations: [
          'workspace'
        ]
        transformKql: 'source'
        outputStream: 'Custom-${pricingTableName}'
      }
    ]
  }
}

resource actualCostDcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: 'dcr-finops-cost-${resourceToken}'
  location: location
  kind: 'Direct'
  tags: tags
  properties: {
    streamDeclarations: {
      '${actualCostStream}': {
        columns: actualCostTable.properties.schema.columns
      }
    }
    destinations: {
      logAnalytics: [
        {
          name: 'workspace'
          workspaceResourceId: logAnalytics.id
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          actualCostStream
        ]
        destinations: [
          'workspace'
        ]
        transformKql: 'source'
        outputStream: 'Custom-${actualCostTableName}'
      }
    ]
  }
}

output workspaceResourceId string = logAnalytics.id
output logAnalyticsName string = logAnalytics.name
output applicationInsightsName string = applicationInsights.name
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output pricingDcrName string = pricingDcr.name
output pricingDcrImmutableId string = pricingDcr.properties.immutableId
output pricingDcrEndpoint string = pricingDcr.properties.endpoints.logsIngestion
output pricingStream string = pricingStream
output actualCostDcrName string = actualCostDcr.name
output actualCostDcrImmutableId string = actualCostDcr.properties.immutableId
output actualCostDcrEndpoint string = actualCostDcr.properties.endpoints.logsIngestion
output actualCostStream string = actualCostStream
