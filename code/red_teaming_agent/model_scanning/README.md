# Model Scanning - Red Teaming Agent

Cloud-based red teaming scans for AI models using Azure AI Foundry's OpenAI Evals API with **Model** target type.

## Quick Start

```bash
pip install -r requirements.txt
az login

# 1. Copy and fill env vars
cp .env.sample .env
# Edit .env with your Foundry project endpoint and model deployment names

# 2. Run scans
python cloud_scan.py                                          # uses .env defaults
python cloud_scan.py --models gpt-5-1 gpt-5-3 --difficulty moderate
python cloud_scan.py --difficulty all --no-wait                # fire-and-forget
python cloud_scan.py --models gpt-5-1 --difficulty easy --timeout 45
```

## Configuration

All configuration is via environment variables (see [.env.sample](.env.sample)) or CLI flags.

| Flag | Env Var | Required | Default | Description |
|------|---------|----------|---------|-------------|
| `--endpoint` | `AZURE_AI_PROJECT_ENDPOINT` | **Yes** | — | `https://<account>.services.ai.azure.com/api/projects/<project>` |
| `--models` | `RED_TEAM_MODELS` | **Yes** | — | Comma-separated deployment names |
| `--difficulty` | `RED_TEAM_DIFFICULTY` | No | `easy` | `easy` / `moderate` / `difficult` / `all` |
| `--num-turns` | `RED_TEAM_NUM_TURNS` | No | `1` | Simulation rounds per attack |
| `--timeout` | `RED_TEAM_TIMEOUT_MINUTES` | No | `30` | Poll timeout in minutes |
| `--no-wait` | — | No | — | Don't poll for completion |

## Difficulty Levels

| Level | Strategies | Description |
|-------|-----------|-------------|
| `easy` | Base64, Flip, Morse | Encoding-based attacks |
| `moderate` | Tense | Semantic rephrasing |
| `difficult` | Crescendo, Multiturn | Multi-step attacks |
| `all` | Base64, Flip, Morse, Tense | Combined easy + moderate |

## Supported Models

Only **OpenAI-compatible** deployments work with the cloud `azure_ai_model` target.

| Target Type | Examples | Supported |
|------------|---------|-----------|
| OpenAI / GPT | gpt-5-1, gpt-5-3, gpt-5-4, gpt-4o | ✅ |
| Azure AI Inference (Mistral, Claude) | mistral-document-ai, claude-* | ❌ (completes with 0 results) |

## Safety Evaluators

6 built-in evaluators (v3): Violence, Self-Harm, Sexual, Hate & Unfairness, Ungrounded Attributes, Code Vulnerability.

## Results

- Saved to `results/` as JSON
- Visible in [Foundry portal](https://ai.azure.com) → **Evaluations > Red team** tab
- Key metric: **Attack Success Rate (ASR)** — percentage of attacks that elicit undesirable responses
