targetScope = 'resourceGroup'

@description('Existing Microsoft Foundry account that already contains the engagement project.')
param accountName string

@description('Anthropic deployment name recorded by the accelerator target profile.')
param deploymentName string = 'rta-anthropic'

@description('Anthropic model name verified in the live regional catalog.')
param modelName string = 'claude-haiku-4-5'

@description('Exact Anthropic model version verified in the live regional catalog.')
param modelVersion string = '2'

@minValue(1)
param capacity int = 1

@description('Real legal entity accepting the Anthropic Marketplace/provider terms; no sample default is permitted.')
@minLength(1)
param organizationName string

@description('Real two-letter ISO country code; no sample default is permitted.')
@minLength(2)
@maxLength(2)
param countryCode string

@description('Real lowercase industry; no sample default is permitted.')
@allowed([
  'technology'
  'finance'
  'healthcare'
  'education'
  'retail'
  'manufacturing'
  'government'
  'media'
  'other'
])
param industry string

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' existing = {
  name: accountName
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = {
  parent: account
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'Anthropic'
      name: modelName
      version: modelVersion
    }
    #disable-next-line BCP037 // Supported by 2025-10-01-preview; local Bicep type metadata lags the service.
    modelProviderData: {
      organizationName: organizationName
      countryCode: countryCode
      industry: industry
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

output anthropicDeploymentName string = deployment.name