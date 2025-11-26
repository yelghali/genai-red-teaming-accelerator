# GenAI Red Teaming Accelerator

A kickstarter project to easily begin red teaming GenAI applications using [PyRIT (Python Risk Identification Tool)](https://github.com/Azure/PyRIT).

## 🎯 What is This?

This accelerator helps you identify vulnerabilities in AI applications through **red teaming** - proactively testing for prompt injection, jailbreaks, and security issues before adversaries do.

**What you'll learn:**
- AI security concepts and attack surfaces
- Red teaming demo applications (HTTP API & web chatbot)
- Configuring PyRIT for your own applications
- Automating security scans in CI/CD pipelines

**Estimated time:** 80 minutes

## 📚 Workshop Tutorial

👉 **[Complete Workshop Tutorial](https://moaw.dev/workshop/?src=gh:yelghali/genai-red-teaming-accelerator/main/docs/)**

The tutorial includes step-by-step modules, interactive notebooks, hands-on exercises, and production deployment guides.

---

## ⚡ Quick Start (TL;DR)

```bash
# 1. Clone and setup
git clone https://github.com/yelghali/genai-red-teaming-accelerator.git
cd genai-red-teaming-accelerator
cp code/.env.example code/.env
# Edit code/.env with your Azure OpenAI credentials

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Start demo applications
cd code/demo_target_apps
python run_demo_apps.py

# 4. In another terminal, open Jupyter notebooks
cd code/notebooks
jupyter notebook
# Open api_target.ipynb and follow along
```

**For detailed instructions, see the [Workshop Tutorial](https://moaw.dev/workshop/?src=gh:yelghali/genai-red-teaming-accelerator/main/docs/).**

---

## 📁 Repository Structure

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
