# Running RTA scans

This guide shows the shortest supported path for scanning three target types:

| Target under test | Target catalog | Test profile | Execution engine |
|---|---|---|---|
| OpenAI-compatible or Foundry model deployment | `configs/pyrit/targets.yaml` | `configs/redteam.yaml` | Native PyRIT |
| Foundry model with a portal-visible evaluation | `configs/foundry.yaml` | `configs/redteam.yaml` | Foundry cloud |
| JSON HTTP API | `configs/examples/api-targets.yaml` | `configs/examples/api-redteam.yaml` | Native PyRIT |
| Browser chat UI, including form login | `configs/examples/ui-targets.yaml` | `configs/examples/ui-redteam.yaml` | Native PyRIT + Playwright |

Run every command from the repository root. `rta validate`, `rta list`, and `rta plan` are offline: they validate files
and references but do not call a target or create a cloud evaluation. `rta run` sends real requests and therefore
requires written authorization, target authentication, and `REDTEAM_SCOPE_APPROVED=true`.

## 1. Install once

Use Python 3.11 or 3.12 and the repository's required Microsoft package-feed proxy:

```powershell
$env:PIP_INDEX_URL = "https://packagefeedproxy.microsoft.io/pypi/simple"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,foundry,playwright]"
playwright install chromium
```

Confirm the command is installed:

```powershell
rta --help
```

## 2. Understand the two model roles

A PyRIT scan normally has two distinct model roles:

1. **Objective target** — the model, API, or browser application being tested.
2. **PyRIT helper model** — an OpenAI-compatible model used by native attacks for adversarial prompt generation and
   response scoring.

The catalog's top-level `scorer_target` selects the helper model. In the checked-in Foundry catalog,
`foundry-openai` is the default objective target and `foundry-mistral` is the helper model. The API and UI examples
contain a placeholder `scorer-model`; replace its endpoint, model name, and environment-backed credential before
execution.

A Foundry cloud evaluation is different: Foundry owns objective generation and evaluation. It does not use the
catalog's `scorer_target`.

## 3. Scan a model with native PyRIT

Use this path for an OpenAI-compatible Chat Completions or Responses endpoint, including a Foundry deployment.

### Configure the target

Edit [configs/pyrit/targets.yaml](../configs/pyrit/targets.yaml). Each `openai` target needs:

- the API endpoint and deployment/model name;
- `api: chat` or `api: responses`;
- either identity authentication with a token scope, or an environment-backed API key;
- a bounded `max_requests_per_minute`.

Identity authentication, as used by the checked-in Foundry targets:

```yaml
target:
  type: openai
  provider: foundry
  endpoint: https://<account>.services.ai.azure.com/api/projects/<project>/openai/v1/
  model: <deployment-name>
  api: chat
  auth: identity
  token_scope: https://ai.azure.com/.default
```

API-key authentication for another OpenAI-compatible service:

```yaml
target:
  type: openai
  provider: openai-compatible
  endpoint: https://model.example.com/v1/
  model: <model-name>
  api: chat
  auth: api_key
  api_key:
    source: env
    name: TARGET_MODEL_API_KEY
```

The target name must match the `pyrit_target` binding in [configs/redteam.yaml](../configs/redteam.yaml). Select an
existing profile or copy one and change its logical `target`. Profiles define risks or custom objectives, attack
strategies, turn depth, concurrency, and result labels.

### Validate, plan, and run

For the checked-in Foundry deployments:

```powershell
az login
rta validate --config configs/redteam.yaml
rta plan baseline-pyrit --config configs/redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
rta run baseline-pyrit --config configs/redteam.yaml
```

To run the custom YAML objectives against the same model:

```powershell
$env:REDTEAM_SCOPE_APPROVED = "true"
rta run custom-pyrit --config configs/redteam.yaml
```

For API-key authentication, set the variable named by `api_key` before `rta run`:

```powershell
$env:TARGET_MODEL_API_KEY = "<enter outside source control>"
```

Do not put the key in YAML or pass it as a command-line argument.

### Optional one-objective native smoke test

The checked-in catalog includes one harmless canary dataset. This command bypasses the RTA selector and calls native
PyRIT directly:

```powershell
$env:REDTEAM_SCOPE_APPROVED = "true"
pyrit_scan airt.jailbreak `
  --config-file configs/pyrit/pyrit-config.yaml `
  --start-server `
  --target foundry-openai `
  --techniques prompt_sending `
  --dataset-names foundry-canary `
  --max-dataset-size 1 `
  --max-concurrency 1 `
  --include-baseline false `
  --jailbreak-names aligned.yaml `
  --num-jailbreak-attempts 1
```

## 4. Create a portal-visible Foundry model evaluation

Use this path only when the result must be a Foundry evaluation/run visible in the portal.

1. Edit [configs/foundry.yaml](../configs/foundry.yaml) with the exact project endpoint, publisher, deployment, model,
   and version reported by the live resource.
2. Keep a target blocked with `ready: false` until all metadata and provider prerequisites are verified.
3. Bind its scan name through `foundry_scan` in [configs/redteam.yaml](../configs/redteam.yaml).
4. Use a baseline setup. Foundry cloud model runs do not accept the repository's arbitrary custom-objective YAML.

Inspect without creating a resource:

```powershell
foundry-scan validate --config configs/foundry.yaml
foundry-scan list --config configs/foundry.yaml
rta plan baseline-foundry --config configs/redteam.yaml --json
```

Create the evaluation only after the provider-managed workload is approved:

```powershell
az login
$env:REDTEAM_SCOPE_APPROVED = "true"
rta run baseline-foundry --config configs/redteam.yaml
```

The command returns the Foundry evaluation and run IDs. JSON evidence is written under `artifacts/foundry`, and a
completed run is imported into Co-PyRIT as a labeled `foundry_cloud_snapshot`. Foundry remains the authoritative
record.

## 5. Scan a JSON HTTP API

Start from [configs/examples/api-targets.yaml](../configs/examples/api-targets.yaml) and
[configs/examples/api-redteam.yaml](../configs/examples/api-redteam.yaml).

### Configure the catalog

Replace every placeholder before execution. Structural validation does not prove that an `example.com` URL or a
`replace-with-*` model exists.

1. In `scorer-model`, set the PyRIT helper model endpoint and model name.
2. In `application-api`, set `url`, HTTP method, headers, body template, and response path.
3. Keep sensitive headers as environment references. `prefix: "Bearer "` safely composes an Authorization value.
4. Put `{PROMPT}` where the generated objective belongs in `body_template`.
5. Choose the matching `prompt_encoding`:
   - `json_string` inside a quoted JSON string;
   - `json_value` when the placeholder replaces an entire JSON value;
   - `url` for URL encoding;
   - `raw` only when the endpoint requires unescaped text.
6. Set `response_json_path` to the assistant text, for example `choices[0].message.content`.
7. Keep timeout, request rate, turn depth, and concurrency within the approved limits.

### Set secrets and run

The checked example references these variables:

```powershell
$env:SCORER_API_KEY = "<PyRIT helper-model key>"
$env:TARGET_API_TOKEN = "<target bearer token>"
$env:TARGET_TENANT_KEY = "<target tenant key>"
```

If the API does not use one of those headers, remove that header and its variable reference from the catalog.

Validate and inspect the exact request plan before sending traffic:

```powershell
rta validate --config configs/examples/api-redteam.yaml
rta plan --config configs/examples/api-redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
rta run --config configs/examples/api-redteam.yaml
```

A `401` or `403` is target authentication, not a PyRIT configuration error. A response-extraction exception usually
means `response_json_path` does not match the API's actual JSON response.

## 6. Scan an authenticated browser UI

Start from [configs/examples/ui-targets.yaml](../configs/examples/ui-targets.yaml) and
[configs/examples/ui-redteam.yaml](../configs/examples/ui-redteam.yaml). Chromium must be installed with Playwright.

### Configure the catalog

1. Replace the `scorer-model` placeholders with the PyRIT helper model.
2. Set `application-ui.url` to the login or chat landing page.
3. Define ordered `auth_steps`:
   - `fill` reads its value only from an environment variable;
   - `click` activates a control;
   - `press` handles key-driven login flows;
   - `wait_for` waits for `attached`, `detached`, `visible`, or `hidden` state.
4. Set stable chat selectors:
   - `ready` — post-login element proving chat is usable;
   - `prompt_input` — text input or textarea;
   - `submit` — send control;
   - `response` — assistant-message elements;
   - `file_input` — optional upload input for image prompts.
5. Keep `max_concurrency: 1`. One native Playwright target owns one authenticated page; RTA serializes page
   interactions to prevent prompts and responses from interleaving.

Use browser developer tools to prefer stable IDs, names, or `data-*` attributes over generated CSS classes.

### Set secrets and run

```powershell
$env:SCORER_API_KEY = "<PyRIT helper-model key>"
$env:TARGET_UI_USERNAME = "<test account username>"
$env:TARGET_UI_PASSWORD = "<test account password>"

rta validate --config configs/examples/ui-redteam.yaml
rta plan --config configs/examples/ui-redteam.yaml --json

$env:REDTEAM_SCOPE_APPROVED = "true"
rta run --config configs/examples/ui-redteam.yaml
```

When selectors fail, temporarily set `headless: false`, run one bounded objective, and observe the login and response
flow. Restore headless mode afterward. A UI timeout usually means the readiness selector never became visible, the
submit action did not create a new assistant message, or the response selector matched the wrong element.

## 7. Review results

For native PyRIT model, API, and UI scans, `rta run` prints a scenario result ID and stores the conversations in
PyRIT memory. Start Co-PyRIT against the same local data location:

```powershell
$env:REDTEAM_SCOPE_APPROVED = "true"
pyrit_backend --config-file configs/pyrit/pyrit-config.yaml --host 127.0.0.1 --port 8014
```

Open `http://127.0.0.1:8014/history` and filter using the profile labels such as `test`, `target`, `env`, or `use_case`.
Keep this unauthenticated development UI on loopback.

Foundry cloud runs additionally produce:

- a Foundry evaluation ID and run ID;
- a portal report URL when supplied by the service;
- a local JSON artifact under the configured output directory; and
- an idempotent Co-PyRIT snapshot after successful completion.

## 8. Docker Compose

Local Python is simplest for interactive Azure CLI authentication and UI selector debugging. For container execution:

```powershell
$env:REDTEAM_SCOPE_APPROVED = "true"
docker compose build
docker compose --profile tools run --rm redteam validate --config configs/redteam.yaml
docker compose --profile tools run --rm redteam plan baseline-pyrit --config configs/redteam.yaml --json
```

Rebuild after changing checked-in configuration because the image copies the `configs` directory. Compose passes the
environment variables used by the checked API/UI examples. If a catalog uses different variable names, add them to
the Compose service environment. A local `az login` session is not copied into the container; use an approved workload
identity or service principal for containerized Foundry access.

Start the loopback review UI with the shared data volume:

```powershell
docker compose up -d --wait co-pyrit
```

## 9. Safety checklist before `rta run`

- The target owner approved the exact endpoint, objective data, risks, attack strategies, turn/rate limits, and
  retention.
- Placeholder endpoints and model names were replaced and independently verified.
- Credentials exist only in the environment or an approved identity provider.
- `rta plan` shows the intended target, objective source, techniques, and bounds.
- The target is isolated from production data and side effects, or equivalent controls are documented.
- Co-PyRIT remains bound to `127.0.0.1`.
