# Model Scanning - Red Teaming Agent

Unified red teaming scans for AI models — both **chat models** (cloud) and **document AI** (local callback).

## Quick Start

```bash
pip install -r requirements.txt
az login

# 1. Copy and fill env vars
cp .env.sample .env

# 2. Scan everything (chat models via cloud, Document AI via local callback)
python scan.py --models gpt-5-1 gpt-5-3 mistral-large-3 mistral-document-ai

# 3. Or use env vars
RED_TEAM_MODELS=gpt-5-1,mistral-large-3,mistral-document-ai python scan.py

# Chat models only (cloud)
python cloud_scan.py --models gpt-5-1 gpt-5-3 --difficulty moderate

# All options
python scan.py --models gpt-5-1 mistral-document-ai --difficulty easy --no-wait
```

## Scripts

| Script | Purpose |
|--------|---------|
| **`scan.py`** | Unified scanner — auto-routes chat models to cloud, Document AI to local callback |
| `cloud_scan.py` | Cloud-only scanner for chat models (evals API, `azure_ai_model` target) |

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

Any **chat-completion** model deployed in the Foundry project works with the `azure_ai_model` target.

| Model Type | Examples | Supported |
|------------|---------|-----------|
| OpenAI GPT | gpt-5-1, gpt-5-3, gpt-5-4, gpt-4o | ✅ |
| Mistral Chat | mistral-large-3, mistral-small | ✅ |
| Claude (with quota) | claude-sonnet-4-5, claude-haiku-4-5 | ✅ (needs quota approval) |
| Document/OCR models | mistral-document-ai | ❌ (expects image/PDF input, not text) |

### Mistral Document AI

`mistral-document-ai` is an OCR/document model with a `/v1/ocr` API — not a chat model. The cloud red team `azure_ai_model` target sends chat prompts which don't match its input format, so scans complete with 0 results.

The OCR endpoint requires a **serverless deployment URL** (not the standard AI Services URL) and accepts base64-encoded images/PDFs.

**Red teaming approach for Document AI:**
- Use the local `RedTeam` SDK (`azure-ai-evaluation[redteam]`) with a custom callback that:
  1. Creates a PDF/image with adversarial text embedded (prompt injection, unsafe content)
  2. Sends it to the `/v1/ocr` endpoint
  3. Returns the OCR output text for evaluation
- Best risk categories: **Code Vulnerability** (prompt injection in documents), **Violence** / **Hate & Unfairness** (unsafe content extraction)

## Safety Evaluators

6 built-in evaluators (v3): Violence, Self-Harm, Sexual, Hate & Unfairness, Ungrounded Attributes, Code Vulnerability.

## Results

- Saved to `results/` as JSON
- Visible in [Foundry portal](https://ai.azure.com) → **Evaluations > Red team** tab
- Key metric: **Attack Success Rate (ASR)** — percentage of attacks that elicit undesirable responses
