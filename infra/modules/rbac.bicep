param functionPrincipalId string
param grafanaPrincipalId string
param deployerPrincipalId string
param storageAccountName string
param logAnalyticsName string
param grafanaName string
param pricingDcrName string
param actualCostDcrName string

var storageBlobContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var monitoringMetricsPublisherRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '3913510d-42f4-4e42-8a64-420c390055eb'
)
var monitoringReaderRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '43d0d8ad-25c7-4714-9337-8ba259a9fe05'
)
var logAnalyticsReaderRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '73c42c96-874c-492b-b04d-ab87d138a893'
)
var grafanaAdminRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '22926164-76b3-42b3-bc55-97df8dab3e41'
)

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

resource grafana 'Microsoft.Dashboard/grafana@2023-09-01' existing = {
  name: grafanaName
}

resource pricingDcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' existing = {
  name: pricingDcrName
}

resource actualCostDcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' existing = {
  name: actualCostDcrName
}

resource functionStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functionPrincipalId, storageBlobContributorRoleId)
  properties: {
    roleDefinitionId: storageBlobContributorRoleId
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource deployerPricingIngestionRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: pricingDcr
  name: guid(pricingDcr.id, deployerPrincipalId, monitoringMetricsPublisherRoleId)
  properties: {
    roleDefinitionId: monitoringMetricsPublisherRoleId
    principalId: deployerPrincipalId
  }
}

resource functionCostIngestionRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: actualCostDcr
  name: guid(actualCostDcr.id, functionPrincipalId, monitoringMetricsPublisherRoleId)
  properties: {
    roleDefinitionId: monitoringMetricsPublisherRoleId
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource grafanaMonitoringReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, grafanaPrincipalId, monitoringReaderRoleId)
  properties: {
    roleDefinitionId: monitoringReaderRoleId
    principalId: grafanaPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource grafanaLogReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: logAnalytics
  name: guid(logAnalytics.id, grafanaPrincipalId, logAnalyticsReaderRoleId)
  properties: {
    roleDefinitionId: logAnalyticsReaderRoleId
    principalId: grafanaPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource deployerGrafanaAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: grafana
  name: guid(grafana.id, deployerPrincipalId, grafanaAdminRoleId)
  properties: {
    roleDefinitionId: grafanaAdminRoleId
    principalId: deployerPrincipalId
  }
}
