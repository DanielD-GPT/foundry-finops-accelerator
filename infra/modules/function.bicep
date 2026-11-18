param name string
param planName string
param identityName string
param location string
param applicationInsightsName string
param storageAccountName string
param deploymentContainerName string
param maximumInstanceCount int = 10
param appSettings object = {}
param tags object = {}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'identity'
  params: {
    name: identityName
    location: location
    tags: tags
  }
}

module plan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'plan'
  params: {
    name: planName
    location: location
    reserved: true
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    tags: tags
  }
}

var functionSettings = union(appSettings, {
  AzureWebJobsStorage__blobServiceUri: storage.properties.primaryEndpoints.blob
  AzureWebJobsStorage__queueServiceUri: storage.properties.primaryEndpoints.queue
  AzureWebJobsStorage__credential: 'managedidentity'
  AzureWebJobsStorage__clientId: identity.outputs.clientId
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString
  APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'ClientId=${identity.outputs.clientId};Authorization=AAD'
  AZURE_CLIENT_ID: identity.outputs.clientId
})

module functionApp 'br/public:avm/res/web/site:0.15.1' = {
  name: 'function-app'
  params: {
    name: name
    location: location
    kind: 'functionapp,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [
        identity.outputs.resourceId
      ]
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentContainerName}'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: identity.outputs.resourceId
          }
        }
      }
      scaleAndConcurrency: {
        instanceMemoryMB: 512
        maximumInstanceCount: maximumInstanceCount
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    appSettingsKeyValuePairs: functionSettings
    tags: union(tags, {
      'azd-service-name': 'cost-normalizer'
    })
  }
}

output name string = functionApp.outputs.name
output principalId string = identity.outputs.principalId
output clientId string = identity.outputs.clientId
