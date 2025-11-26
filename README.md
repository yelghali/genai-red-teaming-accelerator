# GenAI Red Teaming Accelerator

A comprehensive framework for automated security testing of GenAI applications using [PyRIT (Python Risk Identification Tool)](https://github.com/Azure/PyRIT).

## 🎯 What This Accelerator Provides

### Progressive Learning Path
1. **Interactive Notebooks** → Learn PyRIT orchestrators hands-on
2. **Demo Applications** → Practice on safe local targets
3. **Non-Interactive Scanning** → Automate security testing
4. **CI/CD Integration** → Production-ready GitHub Actions

### Key Features
- ✅ **Dual Target Support**: Test both HTTP APIs and web applications
- ✅ **Multiple Attack Strategies**: Crescendo, PAIR, Red Teaming, and more
- ✅ **Flexible Deployment**: Local Python, Docker, or GitHub Actions
- ✅ **Production Ready**: Pre-configured CI/CD workflows

---

## 🚀 Quick Start

### Option 1: Learn with Notebooks (Recommended First)

```bash
# 1. Setup environment
cp code/.env.example code/.env
# Edit code/.env with your Azure OpenAI credentials

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Start demo applications
cd code/demo_target_apps
python run_demo_apps.py

# 4. Open notebooks in VS Code or Jupyter
cd ../notebooks
# Work through: api_target.ipynb, playwright_target.ipynb
```

### Option 2: Run Automated Scans

```bash
# 1. Configure your target
nano code/scan/config.py

# 2. Run scan locally
cd code/scan
python run_pyrit_scan.py

# OR with Docker
./run-docker-scan.sh
```

### Option 3: GitHub Actions (Production)

```bash
# 1. Add GitHub Secrets:
#    - AZURE_OPENAI_ENDPOINT
#    - AZURE_OPENAI_KEY
#    - AZURE_OPENAI_DEPLOYMENT

# 2. Configure targets in code/scan/config.py

# 3. Push to repository
git add code/scan/config.py
git commit -m "Configure production scanning"
git push

# 4. Run from Actions tab or wait for schedule
```

---

## 📁 Project Structure

```
genai-red-teaming-accelerator/
├── code/
│   ├── .env                          # Shared Azure OpenAI credentials (gitignored)
│   ├── .env.example                  # Template for credentials
│   │
│   ├── notebooks/                    # 📓 Interactive Learning
│   │   ├── api_target.ipynb                # HTTP API red teaming tutorial
│   │   ├── playwright_target.ipynb         # Web app red teaming tutorial
│   │   └── red_teaming_agent.ipynb         # Advanced techniques
│   │
│   ├── scan/                         # 🤖 Automated Scanning
│   │   ├── config.py                       # Scan configuration ⭐ EDIT THIS
│   │   ├── run_pyrit_scan.py               # Scanner script
│   │   └── scorers/                        # Custom scoring logic
│   │       └── check_fraud_classifier.yaml
│   │
│   └── demo_target_apps/             # 🎯 Practice Targets
│       ├── run_demo_apps.py                # Start both demo apps
│       ├── http_api_app.py                 # FastAPI chatbot (port 8000)
│       ├── playwright_web_app.py           # Flask web chatbot (port 5000)
│       ├── Dockerfile                      # Demo apps container
│       └── docker-compose.yml              # Full stack deployment
│
├── .github/workflows/                # 🔄 CI/CD Automation
│   └── pyrit-scan.yml                      # GitHub Actions workflow
│
├── Dockerfile.pyrit-scan             # Scanner container image
├── run-docker-scan.sh                # Quick Docker runner
├── test-docker-setup.sh              # Verify Docker configuration
├── requirements.txt                  # All Python dependencies
├── requirements-scan.txt             # Scanner-only dependencies
│
├── QUICK_START.md                    # 📖 Detailed setup guide
├── DOCKER_GUIDE.md                   # 🐳 Docker deployment guide
└── README.md                         # 👈 You are here
```

---

## 🎓 Learning Workflow

### Step 1: Interactive Notebooks (1-2 hours)

**Goal**: Understand how PyRIT orchestrators work

1. Start demo apps: `python code/demo_target_apps/run_demo_apps.py`
2. Open `code/notebooks/api_target.ipynb`:
   - Learn HTTP request templates
   - Test PromptSendingOrchestrator
   - Try Crescendo multi-turn attacks
3. Open `code/notebooks/playwright_target.ipynb`:
   - Define browser interaction functions
   - Automate web app testing
   - Combine with scorers

**Why this matters**: Understanding orchestrators interactively helps you configure automated scans correctly.

### Step 2: Non-Interactive Scanning (30 minutes)

**Goal**: Validate configuration for automation

1. Edit `code/scan/config.py`:
   ```python
   TARGET_TYPE = "both"  # Test HTTP and web targets
   ORCHESTRATOR = "crescendo"  # Or ["crescendo", "pair"]
   ```
2. Run: `python code/scan/run_pyrit_scan.py`
3. Review results and logs

**Why this matters**: Ensures your configuration works before deploying to CI/CD.

### Step 3: Production Automation (15 minutes)

**Goal**: Set up continuous security testing

1. Add GitHub Secrets (see below)
2. Update `code/scan/config.py` with production URLs
3. Push to repository
4. Monitor in Actions tab

**Why this matters**: Automated scanning catches regressions and new vulnerabilities.

---

## 🎯 PyRIT Orchestrators Explained

| Orchestrator | Strategy | Best For | Complexity |
|--------------|----------|----------|------------|
| **PromptSendingOrchestrator** | Send single prompts | Basic testing, smoke tests | ⭐ Low |
| **CrescendoOrchestrator** | Gradual escalation | Bypass guardrails, jailbreaks | ⭐⭐ Medium |
| **PAIROrchestrator** | Iterative refinement | Advanced attacks, persistence | ⭐⭐⭐ High |
| **RedTeamingOrchestrator** | Goal-based with scoring | Comprehensive evaluation | ⭐⭐⭐ High |

**Recommendation**: Start with Crescendo for most use cases.

---

## 🎯 Target Types

### HTTP API Target
Tests REST APIs by sending HTTP requests.

**Configuration**:
```python
RAW_HTTP_REQUEST = """
POST https://your-api.com/chat
Content-Type: application/json
Authorization: Bearer {API_KEY}

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

RESPONSE_JSON_PATH = "choices[0].message.content"
```

### Playwright Target
Tests web applications using browser automation.

**Configuration**:
```python
PLAYWRIGHT_URL = "https://your-app.com"
PLAYWRIGHT_INPUT_SELECTOR = "#message-input"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "#send-button"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".bot-message"
```

### Both Targets
Run all orchestrators against both HTTP and web targets:

```python
TARGET_TYPE = "both"
ORCHESTRATOR = ["crescendo", "pair"]
# Results in: Crescendo+HTTP, Crescendo+Web, PAIR+HTTP, PAIR+Web
```

---

## ⚙️ Deployment Options

### 1. Local Python (Development)
**Best for**: Learning, quick iterations, debugging

```bash
cd code/scan
python run_pyrit_scan.py
```

**Pros**: Fast, easy to debug  
**Cons**: Requires local setup

### 2. Docker (Testing)
**Best for**: Isolated testing, consistency validation

```bash
./run-docker-scan.sh
```

**Pros**: Consistent environment, no local dependencies  
**Cons**: Slower build times

### 3. GitHub Actions (Production)
**Best for**: Automated CI/CD, scheduled scans, production monitoring

**Triggers**:
- Manual: Actions tab → "Run workflow"
- Scheduled: Daily at 2 AM UTC
- Automatic: On push to `code/scan/` files

**Pros**: Fully automated, audit trail, no infrastructure needed  
**Cons**: GitHub Actions minutes usage

---

## 🔧 Configuration Guide

### GitHub Secrets Required

| Secret Name | Example Value | Purpose |
|-------------|---------------|---------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` | Azure OpenAI base URL |
| `AZURE_OPENAI_KEY` | `abc123...` | API authentication |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | `2024-02-15-preview` | API version |

### Environment File (`code/.env`)

```env
OPENAI_CHAT_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions
OPENAI_CHAT_API_KEY=your-api-key-here
OPENAI_CHAT_MODEL=your-deployment-name
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Important**: Never commit `.env` to git (it's gitignored).

---

## 📊 Example Use Cases

### Scenario 1: Test Customer Support Chatbot

```python
# code/scan/config.py
TARGET_TYPE = "both"
ORCHESTRATOR = ["crescendo", "red_teaming"]

RAW_HTTP_REQUEST = """
POST https://api.example.com/support/chat
Content-Type: application/json
{
    "message": "{PROMPT}",
    "session_id": "{CONVERSATION_ID}"
}
"""

PLAYWRIGHT_URL = "https://chat.example.com"
```

### Scenario 2: Daily Security Scans

```yaml
# .github/workflows/pyrit-scan.yml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
```

### Scenario 3: Pre-Deployment Validation

```yaml
# .github/workflows/pyrit-scan.yml
on:
  pull_request:
    paths:
      - 'src/chatbot/**'
```

---

## 📖 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **README.md** | Overview and quick reference | Everyone |
| **[QUICK_START.md](QUICK_START.md)** | Step-by-step setup guide | New users |
| **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** | Docker deployment details | DevOps |
| **[docs/workshop.md](docs/workshop.md)** | Comprehensive workshop | Advanced users |

---

## 🛠️ Requirements

### Software
- **Python 3.11+** - Core runtime
- **Docker** (optional) - Containerized deployment
- **Git** - Version control
- **VS Code** (recommended) - Notebook editing

### Azure Services
- **Azure OpenAI** - GPT-4 or GPT-4o deployment
- **GitHub** (optional) - CI/CD automation

### Python Packages
See `requirements.txt` for complete list. Key dependencies:
- `pyrit==0.8.1` - Red teaming framework
- `playwright>=1.40.0` - Browser automation
- `openai>=1.0.0` - Azure OpenAI SDK
- `fastapi` + `flask` - Demo applications

---

## 🚦 Getting Started Checklist

### First-Time Setup
- [ ] Clone repository
- [ ] Copy `code/.env.example` to `code/.env`
- [ ] Add Azure OpenAI credentials to `code/.env`
- [ ] Install: `pip install -r requirements.txt`
- [ ] Install browsers: `playwright install chromium`

### Interactive Learning
- [ ] Start demo apps: `python code/demo_target_apps/run_demo_apps.py`
- [ ] Complete `api_target.ipynb` notebook
- [ ] Complete `playwright_target.ipynb` notebook
- [ ] Understand orchestrator differences

### Automated Scanning
- [ ] Configure `code/scan/config.py` for your target
- [ ] Test locally: `python code/scan/run_pyrit_scan.py`
- [ ] Verify results and logs
- [ ] (Optional) Test with Docker: `./run-docker-scan.sh`

### Production Deployment
- [ ] Add GitHub Secrets
- [ ] Update config.py with production URLs
- [ ] Test manual workflow run
- [ ] Enable scheduled scans
- [ ] Set up monitoring/alerting

---

## 🤝 Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to grant us the rights to use your contribution.

For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately. Simply follow the instructions provided by the bot.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).

For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ™️ Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).

Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party's policies.
