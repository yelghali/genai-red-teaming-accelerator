# Model Scanning - Red Teaming Agent

Cloud-based red teaming scans for AI models using Azure AI Foundry's OpenAI Evals API with **Model** target type.

## Quick Start

```bash
pip install "azure-ai-projects>=2.0.0" azure-identity
az login

# Scan deployed GPT + Mistral models (easy difficulty)
python cloud_scan.py --difficulty easy --no-wait

# Scan specific models
python cloud_scan.py --models gpt-5-1 gpt-5-3 --difficulty moderate

# Scan all models including Claude (needs quota)
python cloud_scan.py --all --difficulty all --no-wait

# Wait for results
python cloud_scan.py --models gpt-5-1 --difficulty easy --timeout 45
```

## Parameters

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--models` | `RED_TEAM_MODELS` (comma-sep) | GPT + Mistral | Deployment names to scan |
| `--difficulty` | `RED_TEAM_DIFFICULTY` | `easy` | `easy`/`moderate`/`difficult`/`all` |
| `--num-turns` | `RED_TEAM_NUM_TURNS` | `1` | Simulation rounds per attack |
| `--timeout` | `RED_TEAM_TIMEOUT_MINUTES` | `30` | Poll timeout in minutes |
| `--endpoint` | `AZURE_AI_PROJECT_ENDPOINT` | (hardcoded) | Foundry project endpoint |
| `--all` | — | — | Scan all 7 models |
| `--no-wait` | — | — | Don't poll for completion |

## Difficulty Levels

| Level | Strategies | Description |
|-------|-----------|-------------|
| `easy` | Base64, Flip, Morse | Encoding-based attacks |
| `moderate` | Tense | Semantic rephrasing |
| `difficult` | Crescendo, Multiturn | Multi-step attacks |
| `all` | Base64, Flip, Morse, Tense | Combined easy + moderate |

## Models

| Deployment | Model | Status |
|-----------|-------|--------|
| `gpt-5-1` | GPT 5.1 | Deployed |
| `gpt-5-3` | GPT 5.3 | Deployed |
| `gpt-5-4` | GPT 5.4 | Deployed |
| `mistral-document-ai` | Mistral Document AI | Deployed |
| `claude-sonnet-4-5` | Claude Sonnet 4.5 | Needs quota |
| `claude-haiku-4-5` | Claude Haiku 4.5 | Needs quota |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 | Needs quota |

## Safety Evaluators

6 built-in evaluators (v3): Violence, Self-Harm, Sexual, Hate & Unfairness, Ungrounded Attributes, Code Vulnerability.

## Results

- Saved to `results/` as JSON
- Visible in [Foundry portal](https://ai.azure.com) → **Evaluations > Red team** tab
- Each eval groups runs per model with ASR (Attack Success Rate) metrics

## Azure Resources

| Resource | Name | Region |
|----------|------|--------|
| AI Services | `my-foundry-yaya` | Sweden Central |
| Project | `proj-default` | Sweden Central |
| Resource Group | `foundry` | — |

The key metric is **Attack Success Rate (ASR)** — the percentage of attacks that successfully elicit undesirable responses.
