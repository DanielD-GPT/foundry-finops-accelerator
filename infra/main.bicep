targetScope = 'subscription'

@minLength(1)
@maxLength(40)
@description('Short environment name used in resource naming and tags.')
param environmentName string

@description('Primary Azure region for Foundry, monitoring, storage, and Functions.')
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

@description('Azure region for Managed Grafana.')
param grafanaLocation string = 'centralus'

@allowed([
  'development'
  'production'
])
@description('Controls retention, storage redundancy, and Function scaling defaults.')
param environmentTier string = 'development'

@description('Existing Foundry resource name. Leave empty to create a resource.')
param existingFoundryName string = ''

@description('Resource group of an existing Foundry resource. Required when existingFoundryName is set.')
param existingFoundryResourceGroup string = ''

@description('Deploy a small Global Standard gpt-5-mini example deployment when creating Foundry.')
param deploySampleModel bool = false

@description('Object ID receiving Grafana Admin for dashboard import.')
param principalId string = deployer().objectId

@description('Deployment timestamp used to create the Cost Management export schedule.')
param deploymentTimestamp string = utcNow()

var abbreviations = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var shortToken = take(resourceToken, 13)
var tags = {
  'azd-env-name': environmentName
  'solution': 'foundry-finops-accelerator'
  'environment-tier': environmentTier
}
var createFoundry = empty(existingFoundryName)
var resourceGroupName = '${abbreviations.resourcesResourceGroups}foundry-finops-${environmentName}'
var foundryName = createFoundry
  ? '${abbreviations.cognitiveServicesAccounts}${environmentName}-${shortToken}'
  : existingFoundryName
var foundryResourceGroupName = createFoundry
  ? resourceGroupName
  : existingFoundryResourceGroup
var retentionDays = environmentTier == 'production' ? 90 : 30
var storageSku = environmentTier == 'production' ? 'Standard_ZRS' : 'Standard_LRS'

resource acceleratorResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: acceleratorResourceGroup
  params: {
    location: location
    resourceToken: shortToken
    retentionDays: retentionDays
    tags: tags
  }
}

module storage './modules/storage.bicep' = {
  name: 'storage'
  scope: acceleratorResourceGroup
  params: {
    location: location
    name: '${abbreviations.storageStorageAccounts}${take(replace(environmentName, '-', ''), 8)}${shortToken}'
    skuName: storageSku
    tags: tags
  }
}

module foundry './modules/foundry.bicep' = if (createFoundry) {
  name: 'foundry'
  scope: acceleratorResourceGroup
  params: {
    location: location
    name: foundryName
    deploySampleModel: deploySampleModel
    tags: tags
  }
}

module foundryMonitoring './modules/foundry-monitoring.bicep' = {
  name: 'foundry-monitoring'
  scope: resourceGroup(foundryResourceGroupName)
  params: {
    foundryName: foundryName
    workspaceResourceId: monitoring.outputs.workspaceResourceId
  }
  dependsOn: [
    foundry
  ]
}

module functionApp './modules/function.bicep' = {
  name: 'cost-normalizer'
  scope: acceleratorResourceGroup
  params: {
    location: location
    name: '${abbreviations.webSitesFunctions}finops-${environmentName}-${shortToken}'
    planName: '${abbreviations.webServerFarms}finops-${shortToken}'
    identityName: '${abbreviations.managedIdentityUserAssignedIdentities}finops-${shortToken}'
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    storageAccountName: storage.outputs.storageAccountName
    deploymentContainerName: storage.outputs.deploymentContainerName
    maximumInstanceCount: environmentTier == 'production' ? 20 : 10
    appSettings: {
      COST_NORMALIZER_SCHEDULE: '0 15 3 * * *'
      COST_EXPORT_STORAGE_URL: storage.outputs.blobEndpoint
      COST_EXPORT_CONTAINER: storage.outputs.costExportContainerName
      ACTUAL_COST_DCR_ENDPOINT: monitoring.outputs.actualCostDcrEndpoint
      ACTUAL_COST_DCR_IMMUTABLE_ID: monitoring.outputs.actualCostDcrImmutableId
      ACTUAL_COST_DCR_STREAM: monitoring.outputs.actualCostStream
      FOUNDRY_RESOURCE_ID: resourceId(foundryResourceGroupName, 'Microsoft.CognitiveServices/accounts', foundryName)
      FOUNDRY_RESOURCE_GROUP: foundryResourceGroupName
      AZURE_SUBSCRIPTION_ID: subscription().subscriptionId
      COST_CURRENCY: 'USD'
    }
    tags: tags
  }
}

module grafana './modules/grafana.bicep' = {
  name: 'grafana'
  scope: acceleratorResourceGroup
  params: {
    location: grafanaLocation
    name: take('${abbreviations.dashboardGrafana}${environmentName}-${shortToken}', 23)
    zoneRedundancy: environmentTier == 'production'
    tags: tags
  }
}

module rbac './modules/rbac.bicep' = {
  name: 'rbac'
  scope: acceleratorResourceGroup
  params: {
    functionPrincipalId: functionApp.outputs.principalId
    grafanaPrincipalId: grafana.outputs.principalId
    deployerPrincipalId: principalId
    storageAccountName: storage.outputs.storageAccountName
    logAnalyticsName: monitoring.outputs.logAnalyticsName
    grafanaName: grafana.outputs.name
    pricingDcrName: monitoring.outputs.pricingDcrName
    actualCostDcrName: monitoring.outputs.actualCostDcrName
  }
}

var exportStart = deploymentTimestamp
var exportEnd = dateTimeAdd(deploymentTimestamp, 'P5Y')

resource actualCostExport 'Microsoft.CostManagement/exports@2025-03-01' = {
  name: 'foundry-finops-${environmentName}'
  properties: {
    format: 'Csv'
    compressionMode: 'gzip'
    dataOverwriteBehavior: 'OverwritePreviousReport'
    deliveryInfo: {
      destination: {
        resourceId: storage.outputs.storageAccountResourceId
        container: storage.outputs.costExportContainerName
        rootFolderPath: 'exports'
      }
    }
    definition: {
      type: 'ActualCost'
      timeframe: 'MonthToDate'
      dataSet: {
        granularity: 'Daily'
      }
    }
    schedule: {
      status: 'Active'
      recurrence: 'Daily'
      recurrencePeriod: {
        from: exportStart
        to: exportEnd
      }
    }
  }
}

output AZURE_RESOURCE_GROUP string = acceleratorResourceGroup.name
output AZURE_LOCATION string = location
output GRAFANA_LOCATION string = grafanaLocation
output LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsName
output APPLICATION_INSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output GRAFANA_NAME string = grafana.outputs.name
output GRAFANA_ENDPOINT string = grafana.outputs.endpoint
output FOUNDRY_RESOURCE_NAME string = foundryName
output FOUNDRY_RESOURCE_GROUP string = foundryResourceGroupName
output FOUNDRY_ENDPOINT string = 'https://${foundryName}.openai.azure.com'
output COST_EXPORT_NAME string = actualCostExport.name
output PRICING_DCR_NAME string = monitoring.outputs.pricingDcrName
output ACTUAL_COST_DCR_NAME string = monitoring.outputs.actualCostDcrName
output AZURE_FUNCTION_NAME string = functionApp.outputs.name
