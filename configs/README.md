# Configuration

The shared entry point is [redteam.yaml](redteam.yaml). A test profile selects `engine: pyrit` or `engine: foundry`,
binds one logical target to its native name, and defines baseline or custom coverage. Change `selected_test`, or pass
the profile name to `rta plan|run`. `redteam-run` remains a compatibility alias.

It delegates to two native runtime configurations:

- [pyrit/pyrit-config.yaml](pyrit/pyrit-config.yaml) is a native PyRIT configuration.
- [foundry.yaml](foundry.yaml) configures portal-visible Foundry evaluation-service runs.

Native target definitions live in [pyrit/targets.yaml](pyrit/targets.yaml). Add models, JSON APIs, or browser UIs there;
`pyrit_scan`, `pyrit_shell`, and `pyrit_backend` consume them through [pyrit/initializer.py](pyrit/initializer.py).
Provider and model names are data, not a supported-model enum.

Two PyRIT-only examples keep setup small and are validated in CI:

- [examples/api-redteam.yaml](examples/api-redteam.yaml) selects [examples/api-targets.yaml](examples/api-targets.yaml),
  including environment-backed API headers and Bearer-prefix composition.
- [examples/ui-redteam.yaml](examples/ui-redteam.yaml) selects [examples/ui-targets.yaml](examples/ui-targets.yaml),
  including ordered, environment-backed browser login steps.

The unified runner sets `RTA_PYRIT_TARGETS` to the selected catalog during PyRIT initialization, so each profile uses
the catalog it validates. A PyRIT-only profile can set `runtimes.foundry: null` and omit `foundry_scan`; a Foundry
profile must define both.

Foundry scans are entries in the `scans` map in [foundry.yaml](foundry.yaml). Each entry includes its exact target and
workload, avoiding the previous target/scan/policy/execution file graph.

Custom objectives live in strict YAML under [objectives](objectives). They are supported by native PyRIT profiles.
The Foundry cloud model-run API owns objective generation and does not accept those arbitrary files, so that
engine/setup combination fails validation. Foundry agentic tests use a separately reviewed taxonomy instead.

Both paths require `REDTEAM_SCOPE_APPROVED=true` at execution time. Sensitive values must be environment references;
do not put keys, bearer tokens, signed URLs, or cookies in YAML.
