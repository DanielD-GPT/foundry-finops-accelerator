param name string
param location string
param deploySampleModel bool = false
param tags object = {}

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    customSubDomainName: name
    disableLocalAuth: true
    dynamicThrottlingEnabled: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource sampleModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deploySampleModel) {
  parent: foundry
  name: 'gpt-5-mini'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5-mini'
      version: '2025-08-07'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

output name string = foundry.name
output resourceId string = foundry.id
