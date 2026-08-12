# Foundry test infrastructure

The Bicep template creates one dedicated Microsoft Foundry account/project and loops over a `modelDeployments` array.
Publisher, model, version, SKU, capacity, and deployment name are parameters rather than provider-specific resources.
Its RTA defaults create an equivalent OpenAI/Mistral test environment. Anthropic has a separate opt-in template because
its deployment accepts provider/Marketplace terms and requires real customer attestation metadata.

## Preflight

Before deployment, verify the selected models in the account's live regional catalog, available quota, organizational
Marketplace policy, and operator permissions. Catalog visibility does not guarantee deployment eligibility.

Create a dedicated resource group, obtain the signed-in operator object ID, and deploy the template with an
organization-approved naming convention. Pass `operatorPrincipalId` only when the deployment identity may create role
assignments; otherwise ask an administrator to grant the project-scoped `Foundry User` role.

The default `modelDeployments` value deploys:

| Provider | Deployment | Model/version | SKU/capacity |
|---|---|---|---|
| OpenAI | `rta-openai` | `gpt-5-mini` / `2025-08-07` | `GlobalStandard` / `1` |
| Mistral AI | `rta-mistral` | `Mistral-Large-3` / `1` | `GlobalStandard` / `1` |

Use an approved region confirmed by the live model catalog. Review a what-if before deployment:

```powershell
$resourceGroup = "rg-<engagement>-foundry"
$location = "<approved-region>"
$accountName = "<globally-unique-foundry-account>"
$projectName = "rta-redteam"

az group create --name $resourceGroup --location $location
az deployment group what-if --resource-group $resourceGroup `
	--template-file infra/foundry/main.bicep `
	--parameters accountName=$accountName projectName=$projectName location=$location
az deployment group create --resource-group $resourceGroup `
	--name rta-foundry `
	--template-file infra/foundry/main.bicep `
	--parameters accountName=$accountName projectName=$projectName location=$location
```

For customer environments, pass an approved `modelDeployments` array or parameter file. Each object must contain
`name`, `publisher`, `model`, `version`, `sku`, `capacity`, and `raiPolicyName`. A new publisher/model combination does
not require a Bicep resource or accelerator Python change.

Pass `operatorPrincipalId=<object-id>` only when the deploying identity can create role assignments. The deployment
outputs the project endpoint required by the shared execution profile.

After deployment, copy the project endpoint and exact deployment metadata into `configs/foundry.yaml`. Run
`foundry-scan validate --config configs/foundry.yaml` before creating evaluation traffic.

## Anthropic opt-in

Deploy `anthropic.bicep` only after the customer has reviewed applicable terms and confirmed that the subscription
supports the offer. Its required parameters have no sample defaults. Supply the real:

- legal organization name
- two-letter ISO country code
- lowercase industry from the template's allowed values

Those values are sent as `modelProviderData` and may accept the Marketplace offer on behalf of the organization. The
default template cannot deploy Anthropic, and the opt-in template cannot validate without complete attestation fields.

Capture the values from an authorized representative; do not put invented examples in scripts or parameter files:

```powershell
$organizationName = Read-Host "Legal organization name"
$countryCode = Read-Host "Two-letter ISO country code"
$industry = Read-Host "Approved lowercase industry"

az deployment group what-if --resource-group $resourceGroup `
	--template-file infra/foundry/anthropic.bicep `
	--parameters accountName=$accountName organizationName=$organizationName countryCode=$countryCode industry=$industry
```

Change `what-if` to `create --name rta-anthropic` only after legal, policy, region, and quota review succeeds.

## Security and cleanup

The account uses managed identity and disables local-key authentication. Public network access is enabled for this
portable lab template; production/customer deployments should add their approved network controls.

Use a dedicated resource group so cleanup is explicit. Review the resource inventory and retained evidence, then
delete the resource group when the engagement owner approves cleanup. Partner model soft deletion can retain quota
briefly, so verify quota release before immediately recreating the environment.

```powershell
az resource list --resource-group $resourceGroup --output table
az group delete --name $resourceGroup --yes --no-wait
```
