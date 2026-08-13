# Red Teaming Accelerator (RTA)

A small integration layer for **native PyRIT 1.0.1** and the **Microsoft Foundry cloud red-teaming agent**.

The repository keeps execution in the native products and adds one strict selector:

| Need | Interface | Evidence |
|---|---|---|
| Choose PyRIT or Foundry in YAML | `rta` with [configs/redteam.yaml](configs/redteam.yaml) | Native engine evidence below |
| Run PyRIT scenarios against models, APIs, or browser UIs | Native `pyrit_scan`, `pyrit_shell`, and `pyrit_backend` | PyRIT memory and Co-PyRIT |
| Create a portal-visible Foundry red-team evaluation | `foundry-scan` | Foundry eval/run IDs, portal results, and local JSON |

`rta` is a thin adapter, not a second scanner. For `engine: pyrit`, it calls PyRIT's
`ScenarioRegistry.create_and_initialize_async()` and PyRIT's upstream `foundry.red_team_agent` scenario. For
`engine: foundry`, it calls `azure-ai-projects` evaluation APIs. It contains no attack loop, scorer implementation,
or target protocol. The smaller `foundry-scan` command remains useful for direct submission and reconciliation.
`redteam-run` remains as a compatibility alias; new automation should use `rta`.

## Real models, not a fake chat demo

The old deterministic loopback chat application has been removed. The checked-in configuration identifies two real
deployments in the isolated Foundry project:

| Provider | Deployment | Model/version | Ready |
|---|---|---|---|
| OpenAI | `grta-openai` | `gpt-5-mini` / `2025-08-07` | Yes |
| Mistral AI | `grta-mistral` | `Mistral-Large-3` / `1` | Yes |
| Anthropic | `grta-anthropic` | `claude-haiku-4-5` / `2` | No—subscription Marketplace policy blocks it |

The three deployment values above are existing Azure resource IDs and are intentionally unchanged. RTA-generated names,
containers, volumes, environment variables, and new infrastructure defaults use the `rta` prefix.

Native PyRIT calls OpenAI and Mistral through the Foundry project's OpenAI-compatible **Chat Completions protocol**.
That protocol is only the transport shape; the targets are the real deployed models. The separate Foundry-managed
path creates real evaluation resources in the project and verifies deployment publisher, model, and version before
submission.

## Install

Use Python 3.11 or 3.12. All Python dependencies in this repository are installed from the Microsoft package-feed
proxy at `https://packagefeedproxy.microsoft.io/pypi/simple`; this is the repository package-source policy for local,
dev-container, Docker, and CI installs.

```powershell
$env:PIP_INDEX_URL = "https://packagefeedproxy.microsoft.io/pypi/simple"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,foundry,playwright]"
playwright install chromium
```

The verified runtime contracts are `pyrit==1.0.1` and `azure-ai-projects==2.4.0`.

## Quick start: choose what to scan

Run commands from the repository root. Use `validate` and `plan` first; both are offline. Only `run` sends requests
to a target or creates a Foundry evaluation.

| Target | Configure | Offline check | Authorized execution |
|---|---|---|---|
| Model through native PyRIT | [configs/pyrit/targets.yaml](configs/pyrit/targets.yaml) and the `baseline-pyrit` or `custom-pyrit` profile | `rta plan baseline-pyrit --config configs/redteam.yaml --json` | `rta run baseline-pyrit --config configs/redteam.yaml` |
| Model through Foundry cloud | [configs/foundry.yaml](configs/foundry.yaml) and the `baseline-foundry` profile | `rta plan baseline-foundry --config configs/redteam.yaml --json` | `rta run baseline-foundry --config configs/redteam.yaml` |
| JSON HTTP API | [configs/examples/api-targets.yaml](configs/examples/api-targets.yaml) | `rta plan --config configs/examples/api-redteam.yaml --json` | `rta run --config configs/examples/api-redteam.yaml` |
| Authenticated browser UI | [configs/examples/ui-targets.yaml](configs/examples/ui-targets.yaml) | `rta plan --config configs/examples/ui-redteam.yaml --json` | `rta run --config configs/examples/ui-redteam.yaml` |

Before execution, replace every placeholder endpoint, model name, request shape, response path, or browser selector;
set the referenced environment variables; record written authorization; and then set
`REDTEAM_SCOPE_APPROVED=true`. Structural validation deliberately does not contact placeholder services.

Native PyRIT scans use two model roles: the **objective target** being tested and an OpenAI-compatible **helper
model** used for adversarial prompt generation and response scoring. The API and UI examples therefore require both
the application target and the placeholder `scorer-model` to be configured.

See [docs/running-scans.md](docs/running-scans.md) for complete model, Foundry, API, UI, result-review, troubleshooting,
and Docker instructions.

## Choose the engine in configuration

[configs/redteam.yaml](configs/redteam.yaml) contains selectable tests. Set `selected_test`, or pass a test name to
the command. Every test has:

- `engine: pyrit` or `engine: foundry`
- a logical target that binds to a native PyRIT target and, when used by Foundry, a Foundry scan
- a `baseline` or `custom` setup
- attack strategies, baseline inclusion, turn limit, concurrency, and labels
- labels such as `team`, `env`, and `use_case` that flow into native result metadata

Inspect everything without model calls or cloud-resource creation:

```powershell
rta validate --config configs/redteam.yaml
rta list --config configs/redteam.yaml
rta plan baseline-pyrit --config configs/redteam.yaml --json
rta plan baseline-foundry --config configs/redteam.yaml --json
rta plan custom-pyrit --config configs/redteam.yaml --json
```

After written authorization and authentication, run the selected profile:

```powershell
$env:REDTEAM_SCOPE_APPROVED = "true"
az login
rta run baseline-pyrit --config configs/redteam.yaml
# Or create a portal-visible cloud evaluation:
rta run baseline-foundry --config configs/redteam.yaml
```

The checked-in baseline profiles cover violence, hate/unfairness, sexual content, and self-harm; run direct baseline
probes plus Base64 and Crescendo; and cap Crescendo at three turns. Add other supported risks or strategies in YAML.
PyRIT applies `objective_count.pyrit_per_risk` to each configured risk's dataset group. Foundry cloud currently does
not expose an objective-count input for model runs, so its value is explicitly `service_managed` rather than silently
pretending the same control exists.

### Custom attack objectives

[configs/objectives/custom-policy-checks.yaml](configs/objectives/custom-policy-checks.yaml) is a strict,
user-editable objective file. The `custom-pyrit` profile runs those objectives through PyRIT's baseline and native
Crescendo attack. Add an `id`, objective text, harm categories, and non-secret metadata for each new case.

The current Foundry **cloud model-run** API does not accept an arbitrary custom objective file. A profile combining
`engine: foundry` with `type: custom` is rejected during validation. Foundry agents instead use a separately generated,
human-reviewed evaluation taxonomy for agentic risks. This distinction prevents a custom objective from being
silently replaced with service-generated content.

### Capability matrix

| Capability | Native PyRIT | Foundry cloud |
|---|---|---|
| Baseline safety risks | Named/local PyRIT datasets | Foundry service-generated objectives |
| Custom YAML objectives | Yes | No for cloud model runs |
| Objective count | Configurable per risk | Service-managed |
| Multi-turn depth | Passed to native attacks that expose `max_turns` | `num_turns` in the cloud run |
| Portal-visible evaluation | No | Yes |
| Primary result store | PyRIT memory | Foundry eval/run and JSON artifact |
| Co-PyRIT | Native result | Clearly labeled imported snapshot after completion |

Foundry cloud can redact harmful/adversarial inputs in result samples. Imported Co-PyRIT rows preserve the service
sample exactly as returned and carry `source=foundry_cloud_snapshot`; they never claim that PyRIT executed the run.

## Native PyRIT

The native configuration is [configs/pyrit/pyrit-config.yaml](configs/pyrit/pyrit-config.yaml). Its initializer loads
[configs/pyrit/targets.yaml](configs/pyrit/targets.yaml), registers the real OpenAI and Mistral targets, and adds one
harmless canary dataset. Provider and model names are ordinary YAML values; adding a compatible model does not require
a Python branch.

Authenticate and confirm written authorization:

```powershell
az login
$env:REDTEAM_SCOPE_APPROVED = "true"
```

List the configured targets through PyRIT itself:

```powershell
pyrit_scan --config-file configs/pyrit/pyrit-config.yaml --start-server --list-targets
```

Run the bounded live OpenAI smoke scan directly with PyRIT:

```powershell
pyrit_scan airt.jailbreak `
  --config-file configs/pyrit/pyrit-config.yaml `
  --start-server `
  --target foundry-openai `
  --techniques prompt_sending `
  --dataset-names foundry-canary `
  --max-dataset-size 1 `
  --max-concurrency 1 `
  --memory-labels '{"platform":"foundry","provider":"openai","purpose":"smoke"}' `
  --include-baseline false `
  --jailbreak-names aligned.yaml `
  --num-jailbreak-attempts 1
```

Change only `--target` and the provider label to run the Mistral deployment. Review the approved workload before any
live run; the example is intentionally limited to one harmless objective and one attack technique.

### Shell and Co-PyRIT

Use the same native configuration:

```powershell
pyrit_shell --config-file configs/pyrit/pyrit-config.yaml --start-server --no-animation
pyrit_backend --config-file configs/pyrit/pyrit-config.yaml --host 127.0.0.1 --port 8014
```

Open `http://127.0.0.1:8014/history` for Co-PyRIT. Keep this unauthenticated development service on loopback. Native
scanner records appear in Co-PyRIT because both surfaces use the same PyRIT SQLite memory.

Completed `rta` Foundry profiles can also be reviewed there. The adapter imports each Foundry output item
idempotently with Foundry eval, run, item, risk, strategy, report URL, user labels, evaluator rationale, and model
response provenance. Foundry remains the authoritative cloud record; Co-PyRIT is a local review snapshot.

## Foundry-managed evaluations

[configs/foundry.yaml](configs/foundry.yaml) contains one project and a map of scans. It is generic: each entry carries
its provider, exact Foundry publisher, deployment, model, version, risks, strategies, and turn count.

Offline inspection never creates cloud traffic:

```powershell
foundry-scan validate --config configs/foundry.yaml
foundry-scan list --config configs/foundry.yaml
```

After scope and provider-managed workload are approved:

```powershell
az login
$env:REDTEAM_SCOPE_APPROVED = "true"
foundry-scan run openai --config configs/foundry.yaml --output artifacts/foundry-openai
foundry-scan run mistral --config configs/foundry.yaml --output artifacts/foundry-mistral
```

For asynchronous submission, add `--no-wait`. Refresh that exact run without creating another evaluation:

```powershell
foundry-scan status openai `
  --config configs/foundry.yaml `
  --result artifacts/foundry-openai/foundry-run-<run-id>.json `
  --wait
```

Do not run the blocked Anthropic or placeholder agent entries until their `ready` state and exact metadata are updated
from real resources.

## Docker Compose and dev container

[compose.yaml](compose.yaml) uses one image and one named `rta-pyrit-data` volume for the selector and Co-PyRIT.
The UI is published only on loopback.

```powershell
docker compose build
docker compose --profile tools run --rm redteam validate --config configs/redteam.yaml
docker compose --profile tools run --rm redteam plan baseline-foundry --config configs/redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
docker compose up -d --wait co-pyrit
docker compose --profile tools run --rm redteam run baseline-pyrit --config configs/redteam.yaml
```

Open `http://127.0.0.1:8014/history`. For a Foundry cloud run in Compose, provide workload identity or service
principal environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET`) to the container;
never store them in YAML. The VS Code dev container mounts the same named volume at `/data` and validates all profiles
after creation.

CI validates both engine plans, tests the adapters/importer, builds the Compose image, and starts the Co-PyRIT health
endpoint. It does not submit a cloud evaluation or call a model.

## Security boundaries

- Run only after the owner approves targets, objective data, risks, strategies, turn/rate limits, and retention.
- Both native execution paths require `REDTEAM_SCOPE_APPROVED=true`; offline `validate`, `list`, and `plan` do not.
- Keep API keys, bearer tokens, cookies, production data, and personal data out of configuration and objective files.
- Prefer `DefaultAzureCredential` or environment-backed secret references. Do not pass secrets as command arguments.
- Duplicate YAML keys are rejected, and validation errors omit input values and source lines so pasted secrets are not echoed.
- Every native target must declare `max_requests_per_minute`; there is no implicit unlimited rate.
- Remote targets and Foundry endpoints must use HTTPS; plain HTTP targets are accepted only on loopback for local development.
- Keep Co-PyRIT on `127.0.0.1`; it is a development review surface, not an authenticated multi-user service.
- Treat generated attacks and responses as sensitive. Foundry and PyRIT retention/telemetry boundaries are distinct.

## Scan a customer API

[configs/examples/api-targets.yaml](configs/examples/api-targets.yaml) is a complete JSON API catalog. Change the API
URL, request body, response path, and scorer model, then export the referenced values:

```powershell
$env:TARGET_API_TOKEN = "<enter outside source control>"
$env:TARGET_TENANT_KEY = "<enter outside source control>"
$env:SCORER_API_KEY = "<enter outside source control>"
rta validate --config configs/examples/api-redteam.yaml
rta plan --config configs/examples/api-redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
rta run --config configs/examples/api-redteam.yaml
```

The `Authorization` value is rendered as `Bearer ` plus `TARGET_API_TOKEN`; the secret is never stored in YAML.
Sensitive headers reject literal values, and resolved header values reject line breaks. Dot paths and array indexes such
as `choices[0].message.content` are supported for JSON response extraction.

## Scan an authenticated browser UI

[configs/examples/ui-targets.yaml](configs/examples/ui-targets.yaml) shows an ordered form login followed by chat
selectors. Replace the URL and selectors, then set the environment-backed login and scorer values:

```powershell
$env:TARGET_UI_USERNAME = "<enter outside source control>"
$env:TARGET_UI_PASSWORD = "<enter outside source control>"
$env:SCORER_API_KEY = "<enter outside source control>"
rta validate --config configs/examples/ui-redteam.yaml
rta plan --config configs/examples/ui-redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
rta run --config configs/examples/ui-redteam.yaml
```

Supported login actions are `fill`, `click`, `press`, and `wait_for`. Every `fill` value must be an environment
reference, so usernames, passwords, and tokens do not appear in configuration. Authentication runs after navigation
and before the chat readiness check. Use stable selectors and set `headless: false` temporarily when debugging them.

For an OpenAI-compatible model, add an `openai` entry to a target catalog. For a Foundry deployment, add one scan
under `scans` in [configs/foundry.yaml](configs/foundry.yaml). Test only assets whose owner approved the exact targets,
data, risks, strategies, turns, rates, and retention.

## Repository map

Only a few files implement runtime behavior:

- [src/genai_red_teaming_accelerator/config_io.py](src/genai_red_teaming_accelerator/config_io.py) — loads YAML without echoing source values in parse errors.
- [src/genai_red_teaming_accelerator/redteam_config.py](src/genai_red_teaming_accelerator/redteam_config.py) — strict engine/profile and objective schemas.
- [src/genai_red_teaming_accelerator/redteam.py](src/genai_red_teaming_accelerator/redteam.py) — delegates to native APIs and selects the engine.
- [src/genai_red_teaming_accelerator/pyrit_scenario.py](src/genai_red_teaming_accelerator/pyrit_scenario.py) — passes bounded turn depth into PyRIT's upstream scenario.
- [src/genai_red_teaming_accelerator/foundry_import.py](src/genai_red_teaming_accelerator/foundry_import.py) — imports labeled cloud snapshots into PyRIT memory.
- [src/genai_red_teaming_accelerator/pyrit_initializer.py](src/genai_red_teaming_accelerator/pyrit_initializer.py) — registers configured targets for native PyRIT.
- [src/genai_red_teaming_accelerator/pyrit_targets.py](src/genai_red_teaming_accelerator/pyrit_targets.py) — protocol adapters for OpenAI-compatible, HTTP, and browser targets.
- [src/genai_red_teaming_accelerator/foundry.py](src/genai_red_teaming_accelerator/foundry.py) — Foundry evaluation submission and reconciliation.
- [src/genai_red_teaming_accelerator/foundry_cli.py](src/genai_red_teaming_accelerator/foundry_cli.py) — the Foundry-only command.
- [infra/foundry/main.bicep](infra/foundry/main.bicep) — generic deployment loop for project models.

See [docs/running-scans.md](docs/running-scans.md) for the operational runbook, [docs/workshop.md](docs/workshop.md)
for the guided lab, and [infra/foundry/README.md](infra/foundry/README.md) for infrastructure boundaries.
