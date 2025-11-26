# PyRIT Scan Configuration

This file controls how PyRIT security scans run in GitHub Actions.

## 🔄 Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│  You Edit: pyrit_config.yml                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │ target_type: "both"                                 │    │
│  │ orchestrator: ["crescendo", "pair"]                 │    │
│  │ http:                                               │    │
│  │   endpoint: "http://api:8000/chat"                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow                                    │
│  1. Read pyrit_config.yml                                   │
│  2. Generate config.py from YAML                            │
│  3. Build Docker image                                      │
│  4. Run scan in container                                   │
│  5. Upload results                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Results                                                    │
│  • Workflow summary                                         │
│  • Downloadable artifacts                                   │
│  • Scan logs                                                │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

1. **Edit this file** to configure your scan
2. **Commit and push** to repository
3. **Go to Actions tab** and click "Run workflow"

## Configuration Options

### Target Type
```yaml
target_type: "http"      # Scan HTTP API only
target_type: "playwright" # Scan web application only
target_type: "both"      # Scan both targets
```

### Orchestrator
```yaml
# Single orchestrator
orchestrator: "crescendo"

# Multiple orchestrators
orchestrator:
  - "crescendo"
  - "pair"
  - "red_teaming"
```

**Available orchestrators:**
- `crescendo` - Gradual escalation attack (recommended)
- `pair` - Prompt Automatic Iterative Refinement
- `red_teaming` - Custom red team scenarios
- `prompt_sending` - Direct prompt testing

### HTTP Target Configuration
```yaml
http:
  endpoint: "http://127.0.0.1:8000/chat"  # Your API endpoint
  timeout: 20.0                           # Request timeout in seconds
  use_tls: false                          # Enable TLS/HTTPS
  response_json_path: "choices[0].message.content"  # JSON path to response
```

### Playwright Target Configuration
```yaml
playwright:
  url: "http://127.0.0.1:5000"           # Web app URL
  headless: true                          # Run browser in headless mode
  input_selector: "#message-input"        # CSS selector for input field
  send_button_selector: "#send-button"    # CSS selector for send button
  bot_message_selector: ".bot-message"    # CSS selector for bot responses
```

### General Settings
```yaml
general:
  log_level: "WARNING"  # Options: WARNING, INFO, DEBUG
  scorer_yaml_path: "./scorers/check_fraud_classifier.yaml"
```

## Secrets Required

Set these in GitHub repository secrets:
- `OPENAI_CHAT_ENDPOINT` - Azure OpenAI endpoint URL
- `OPENAI_CHAT_API_KEY` - Azure OpenAI API key
- `OPENAI_CHAT_MODEL` - Model deployment name (e.g., gpt-4.1)

## Workflow Triggers

The scan runs automatically when:
- **Manual:** Click "Run workflow" in Actions tab
- **Scheduled:** Daily at 2 AM UTC
- **On Push:** When this config file is modified

## Example Configurations

### Example 1: Test HTTP API with Crescendo
```yaml
target_type: "http"
orchestrator: "crescendo"
http:
  endpoint: "https://api.example.com/chat"
general:
  log_level: "INFO"
```

### Example 2: Test Web App with Multiple Orchestrators
```yaml
target_type: "playwright"
orchestrator:
  - "crescendo"
  - "pair"
playwright:
  url: "https://webapp.example.com"
  headless: true
general:
  log_level: "DEBUG"
```

### Example 3: Comprehensive Test
```yaml
target_type: "both"
orchestrator:
  - "crescendo"
  - "pair"
  - "red_teaming"
http:
  endpoint: "https://api.example.com/chat"
playwright:
  url: "https://webapp.example.com"
general:
  log_level: "WARNING"
```

## Viewing Results

After the workflow completes:
1. Go to the **Actions** tab
2. Click on the workflow run
3. Check the **Summary** for quick results
4. Download **Artifacts** for detailed logs

## Troubleshooting

**"Configuration file not found"**
- Ensure `.github/workflows/pyrit_config.yml` exists in repository

**"Invalid YAML"**
- Check YAML syntax (proper indentation, no tabs)
- Use a YAML validator

**"Connection refused"**
- Ensure target URLs are accessible from GitHub runners
- Check if services need to be started in workflow

## Need Help?

See [QUICK_START.md](../../QUICK_START.md) and [GITHUB_ACTIONS_DOCKER_GUIDE.md](../../GITHUB_ACTIONS_DOCKER_GUIDE.md) for detailed documentation.
