# GenAI Red Teaming Accelerator

A hands-on learning framework for security testing GenAI applications using [PyRIT (Python Risk Identification Tool)](https://github.com/Azure/PyRIT).

## 🎯 What is This?

This accelerator helps you identify vulnerabilities in AI applications through **red teaming** - proactively testing for prompt injection, jailbreaks, and other security issues before adversaries do.

**What you'll learn:**
- Understand AI security concepts and attack surfaces
- Practice red teaming on demo applications (HTTP API & web chatbot)
- Configure PyRIT to test your own applications
- Automate security scans in CI/CD pipelines

## 📚 Complete Workshop Tutorial

👉 **[Start the Interactive Workshop](https://moaw.dev/workshop/?src=gh:yelghali/genai-red-teaming-accelerator/main/docs/)**

The workshop includes:
- 🎓 Step-by-step guided learning modules
- 💻 Interactive Jupyter notebooks
- 🎯 Hands-on exercises with demo targets
- 🚀 Production deployment guides
- 🐳 Docker and GitHub Actions integration

**Estimated time:** 80 minutes

---

## ⚡ Quick Start (TL;DR)

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
