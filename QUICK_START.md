# GenAI Red Teaming Accelerator - Quick Start

## Workflow: From Interactive Testing to Production

This accelerator follows a progressive workflow to help you learn PyRIT and integrate it into your CI/CD:

```
1. Environment Setup        →  Configure Azure OpenAI credentials
2. Start Demo Apps          →  Launch local test targets
3. Interactive Notebooks    →  Learn PyRIT orchestrators hands-on
4. Non-Interactive Scan     →  Validate configuration for automation
5. GitHub Actions CI/CD     →  Automate red teaming in production
```

## Prerequisites

- **Python 3.11+** installed
- **Azure OpenAI** account with GPT-4 deployment
- **Git** for version control
- **Docker** (optional, for containerized scans)
- **VS Code** (recommended) with Jupyter extension

## Step 1: Environment Setup

### Clone and Configure

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd genai-red-teaming-accelerator

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp code/.env.example code/.env
```

### Configure Azure OpenAI Credentials

Edit `code/.env` with your credentials:

```bash
# Required for all workflows
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
OPENAI_CHAT_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions
OPENAI_CHAT_API_KEY=your-api-key-here
OPENAI_CHAT_MODEL=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Note**: The demo apps and notebooks share the same `.env` file at `code/.env`

## Step 2: Start Demo Applications

The demo apps provide safe local targets for testing PyRIT attacks.

### Launch Both Apps

```bash
cd code/demo_target_apps
python run_demo_apps.py
```

This starts two applications:
- **HTTP API**: http://localhost:8000 (FastAPI endpoint)
- **Web App**: http://localhost:5000 (Flask web chatbot)

Both apps use your Azure OpenAI deployment to respond to prompts.

**Keep this terminal running** while you work through the notebooks and scans.

### Verify Apps are Running

- HTTP API: Open http://localhost:8000/docs for Swagger UI
- Web App: Open http://localhost:5000 in your browser

## Step 3: Interactive Testing with Notebooks

Before automating scans, use notebooks to learn how PyRIT orchestrators work.

### Open Notebooks in VS Code

```bash
# From project root
code code/notebooks/
```

Or use Jupyter:
```bash
cd code/notebooks
jupyter notebook
```

### Run Through Examples

1. **`api_target.ipynb`** - HTTP API Red Teaming
   - Learn basic prompt sending to HTTP APIs
   - Understand HTTP request templates and response parsing
   - Test Crescendo multi-turn attacks
   - See how orchestrators work step-by-step

2. **`playwright_target.ipynb`** - Web App Red Teaming  
   - Automate browser interactions with Playwright
   - Define custom interaction functions
   - Test adversarial conversations against web UIs
   - Combine with scorers for evaluation

### Key Learning Objectives

- **Understand orchestrators**: PromptSendingOrchestrator, CrescendoOrchestrator, PAIROrchestrator
- **Configure targets**: HTTPTarget vs PlaywrightTarget
- **Use prompt converters**: EmojiConverter, SearchReplaceConverter
- **Add scorers**: Evaluate response safety and success

**Important**: Run cells sequentially and observe the outputs. This hands-on experience is crucial before moving to automation.

## Step 4: Non-Interactive Scanning

After understanding PyRIT through notebooks, configure automated scans for CI/CD.

### Configure Your Scan

Edit `code/scan/config.py` to match your target system:

```python
# Target type: "http", "playwright", or "both"
TARGET_TYPE = "both"

# Choose orchestrator(s): "prompt_sending", "crescendo", "pair", "red_teaming"
ORCHESTRATOR = "crescendo"

# HTTP Target Configuration
RAW_HTTP_REQUEST = """
POST http://127.0.0.1:8000/chat
Content-Type: application/json

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

RESPONSE_JSON_PATH = "choices[0].message.content"

# Playwright Target Configuration  
PLAYWRIGHT_URL = "http://127.0.0.1:5000"
PLAYWRIGHT_INPUT_SELECTOR = "#message-input"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "#send-button"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".bot-message"
```

### Test Configuration Locally

Ensure demo apps are still running, then:

```bash
cd code/scan
python run_pyrit_scan.py
```

This executes the configured orchestrator(s) against your targets and saves results.

**Expected Output**:
- Conversation logs showing attack attempts
- Scoring results evaluating responses
- Summary of successful/failed attempts

### Run with Docker (Optional)

For isolated execution with Docker:

```bash
# From project root
./run-docker-scan.sh
```

This builds a container with all dependencies and runs the scan.

For complete Docker setup including demo apps, see **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** for:
- Running demo apps + scanner together with Docker Compose
- Network isolation and container configuration
- Troubleshooting Docker issues

## Step 5: Automate with GitHub Actions

Once your configuration is validated locally, integrate into CI/CD.

### Configure GitHub Secrets

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   - `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
   - `AZURE_OPENAI_KEY` - Your API key
   - `AZURE_OPENAI_DEPLOYMENT` - Your deployment/model name
   - `AZURE_OPENAI_API_VERSION` - API version (e.g., 2024-02-15-preview)

### Update Target URL in config.py

For GitHub Actions, update the target URLs to point to your production endpoints:

```python
# code/scan/config.py
RAW_HTTP_REQUEST = """
POST https://your-production-api.com/chat
Content-Type: application/json
...
"""

PLAYWRIGHT_URL = "https://your-production-webapp.com"
```

### Commit and Push Configuration

```bash
git add code/scan/config.py
git commit -m "Configure production red teaming scan"
git push
```

### Workflow Triggers

The GitHub Action runs:
- **Manual**: Actions tab → "PyRIT Red Team Scan" → Run workflow
- **Scheduled**: Daily at 2 AM UTC (configurable in `.github/workflows/`)
- **On Push**: When scan configuration files are modified

### View Results

1. Go to **Actions** tab in your repository
2. Click on the latest workflow run
3. Check:
   - **Logs**: Full execution details
   - **Artifacts**: Downloadable scan results and reports
   - **Summary**: Quick overview of findings

## Project Structure

```
genai-red-teaming-accelerator/
├── code/
│   ├── .env                    # Shared environment variables (gitignored)
│   ├── .env.example            # Template for environment setup
│   │
│   ├── notebooks/              # Interactive testing and learning
│   │   ├── api_target.ipynb            # HTTP API red teaming
│   │   └── playwright_target.ipynb     # Web app red teaming
│   │
│   ├── scan/                   # Non-interactive automated scans
│   │   ├── config.py                   # Scan configuration (customize this!)
│   │   ├── run_pyrit_scan.py           # Scan execution script
│   │   └── scorers/                    # Scoring configuration files
│   │       └── check_fraud_classifier.yaml
│   │
│   └── demo_target_apps/       # Local test applications
│       ├── run_demo_apps.py            # Start both demo apps
│       ├── http_api_app.py             # FastAPI chatbot
│       └── playwright_web_app.py       # Flask web chatbot
│
├── .github/workflows/          # GitHub Actions automation
│   └── pyrit-scan.yml                  # Automated scan workflow
│
├── requirements.txt            # Python dependencies
├── QUICK_START.md             # This file
└── README.md                  # Project overview
```

## Troubleshooting

### Demo Apps Won't Start
- Verify `.env` file exists at `code/.env` with correct credentials
- Check ports 8000 and 5000 are not already in use
- Ensure all required environment variables are set

### Notebook Execution Errors
- Ensure demo apps are running before executing notebook cells
- Run cells sequentially from top to bottom
- Reinitialize PyRIT if you get memory/state errors

### Scan Fails
- Validate `config.py` settings match your target API structure
- Test with notebooks first to verify target connectivity
- Check Azure OpenAI quota and rate limits

### Playwright Issues on Windows
- Playwright may have limitations in Jupyter on Windows
- Run cells in VS Code with Jupyter extension
- See: https://github.com/microsoft/playwright-python/issues/480

## Complete Workflow Checklist

- [ ] **Environment Setup**
  - [ ] Created `code/.env` with Azure OpenAI credentials
  - [ ] Installed dependencies: `pip install -r requirements.txt`
  
- [ ] **Demo Apps**
  - [ ] Started apps: `python code/demo_target_apps/run_demo_apps.py`
  - [ ] Verified HTTP API: http://localhost:8000/docs
  - [ ] Verified Web App: http://localhost:5000

- [ ] **Interactive Learning**
  - [ ] Completed `api_target.ipynb` - understood HTTP attacks
  - [ ] Completed `playwright_target.ipynb` - understood web attacks
  - [ ] Experimented with different orchestrators

- [ ] **Non-Interactive Scanning**
  - [ ] Configured `code/scan/config.py` for your target
  - [ ] Successfully ran: `python code/scan/run_pyrit_scan.py`
  - [ ] Reviewed scan results and logs

- [ ] **Production Automation**
  - [ ] Added GitHub secrets for Azure OpenAI
  - [ ] Updated config.py with production endpoints
  - [ ] Tested GitHub Actions workflow
  - [ ] Set up scheduled scans

## Next Steps

1. **Customize for your application**: Modify HTTP request templates and Playwright selectors in `config.py`
2. **Add custom scorers**: Create new YAML files in `code/scan/scorers/` for specific threats
3. **Integrate with monitoring**: Export scan results to your security dashboard
4. **Expand orchestrators**: Test PAIR, RedTeaming, and other attack strategies

See `docs/workshop.md` for detailed workshop walkthrough and advanced topics.
