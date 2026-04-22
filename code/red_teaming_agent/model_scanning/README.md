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
