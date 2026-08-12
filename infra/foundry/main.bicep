targetScope = 'resourceGroup'

@description('Azure region whose live Foundry catalog contains every selected model.')
param location string = resourceGroup().location

@description('Globally unique Microsoft Foundry account name.')
@minLength(2)
@maxLength(64)
param accountName string

@description('Foundry project name shared by all provider deployments.')
param projectName string = 'rta-redteam'

@description('Tags applied to the Foundry account and project.')
param tags object = {
  purpose: 'red-teaming-accelerator'
  lifecycle: 'test'
}

@description('Model deployments to create. Publisher, model, version, SKU, and capacity come from the live regional catalog.')
param modelDeployments array = [
  {
    name: 'rta-openai'
    publisher: 'OpenAI'
    model: 'gpt-5-mini'
    version: '2025-08-07'
    sku: 'GlobalStandard'
    capacity: 1
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  {
    name: 'rta-mistral'
    publisher: 'Mistral AI'
    model: 'Mistral-Large-3'
    version: '1'
    sku: 'GlobalStandard'
    capacity: 1
    raiPolicyName: 'Microsoft.DefaultV2'
  }
]

@description('Optional operator object ID for a project-scoped Foundry User assignment.')
param operatorPrincipalId string = ''

@description('Principal type for the optional Foundry User role assignment.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param operatorPrincipalType string = 'User'

var foundryUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '53ca6127-db72-4b80-b1b0-d745d6d5456d'
)

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'RTA Red Team'
    description: 'Dedicated Microsoft Foundry project for an authorized RTA engagement'
  }
}

resource operatorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(operatorPrincipalId)) {
  name: guid(project.id, operatorPrincipalId, foundryUserRoleDefinitionId)
  scope: project
  properties: {
    roleDefinitionId: foundryUserRoleDefinitionId
    principalId: operatorPrincipalId
    principalType: operatorPrincipalType
  }
}

@batchSize(1)
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = [
  for deployment in modelDeployments: {
    parent: account
    name: deployment.name
    sku: {
      name: deployment.sku
      capacity: deployment.capacity
    }
    properties: {
      model: {
        format: deployment.publisher
        name: deployment.model
        version: deployment.version
      }
      versionUpgradeOption: 'NoAutoUpgrade'
      raiPolicyName: deployment.raiPolicyName
    }
    dependsOn: [
      project
      operatorRole
    ]
  }
]

output foundryAccountName string = account.name
output foundryProjectName string = project.name
output foundryProjectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'
output modelDeploymentNames array = [for deployment in modelDeployments: deployment.name]
