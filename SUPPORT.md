# Support

The Red Teaming Accelerator is an open-source sample and does not include a support SLA or Microsoft Customer
Service and Support entitlement.

## Questions, bugs, and feature requests

Search the [existing GitHub issues](https://github.com/yelghali/genai-red-teaming-accelerator/issues) first. If the
problem or request is not already tracked, open a new issue and include:

- the RTA, PyRIT, Python, and optional Foundry SDK versions;
- the operating system and whether the failure occurs locally, in Compose, or in a dev container;
- the command and complete sanitized error output;
- the smallest strict YAML configuration that reproduces the issue; and
- whether `rta validate` and the corresponding offline `rta plan` succeed.

Never attach API keys, bearer tokens, browser credentials, Azure access tokens, personal data, production prompts,
or unredacted red-team evidence. Replace resource names and endpoints when they are not required to reproduce the
problem.

For Azure service availability, quota, billing, identity, Marketplace, or regional model-catalog incidents, use the
support channel associated with the affected Azure subscription. Repository issues cannot investigate service-side
tenant data.

## Security reports

Do not open a public issue for a suspected vulnerability. Follow [SECURITY.md](SECURITY.md) instead.
