---
published: true                        # Optional. Set to true to publish the workshop (default: false)
type: workshop                          # Required.
title: Azure Red Teaming accelerateur            # Required. Full title of the workshop
short_title: Azure Red Teaming accelerateur      # Optional. Short title displayed in the header
description: This is a workshop intends to help you get started with red teaming with guided examples first ; then how to test red teaming on your own applications.  # Required.
level: beginner                         # Required. Can be 'beginner', 'intermediate' or 'advanced'
authors:                                # Required. You can add as many authors as needed      
  - Yassine El Ghali
contacts:                               # Required. Must match the number of 
  - https://www.linkedin.com/in/yelghali/
duration_minutes: 80                    # Required. Estimated duration in minutes
tags: ai, red teaming, security, prompt injection          # Required. Tags for filtering and searching
#banner_url: assets/banner.jpg           # Optional. Should be a 1280x640px image
#video_url: https://youtube.com/link     # Optional. Link to a video of the workshop
#audience: students, devs                      # Optional. Audience of the workshop (students, pro devs, etc.)
#wt_id: <cxa_tracking_id>                # Optional. Set advocacy tracking code for supported links
#oc_id: <marketing_tracking_id>          # Optional. Set marketing tracking code for supported links
#navigation_levels: 2                    # Optional. Number of levels displayed in the side menu (default: 2)
#navigation_numbering: true             # Optional. Enable numbering in the side menu (default: true)
#sections_title:                         # Optional. Override titles for each section to be displayed in the side bar
#   - Section 1 title
#   - Section 2 title
---

# AI Red Teaming Workshop

This is a hands-on guide to security testing GenAI applications using PyRIT. You will learn to : 

* Understand concepts: Learn AI red teaming fundamentals and attack surfaces

* Practice with examples: Run interactive notebooks against demo HTTP API and web chatbot targets

* Explore attack strategies: Experiment with PyRIT tool and guided examples

* Learn how to test your own apps with a simplified configuration

* Automate security: Integrate scanning into CI/CD with Docker and GitHub Actions



---


## 1. Introduction to AI Red Teaming

### What is AI Red Teaming?

AI Red Teaming is the practice of systematically probing AI systems to discover vulnerabilities, safety issues, and unintended behaviors. Unlike traditional software security testing, AI red teaming focuses on:

- **Prompt injection**: Manipulating inputs to override system instructions
- **Jailbreaking**: Bypassing safety guardrails to generate harmful content
- **Data extraction**: Tricking models into revealing training data or system prompts
- **Goal hijacking**: Redirecting the AI's behavior toward unintended objectives

### Why Red Team AI Applications?

AI systems present unique security challenges:

| Challenge | Description |
|-----------|-------------|
| **Non-deterministic behavior** | The same input may produce different outputs |
| **Emergent capabilities** | Large models exhibit unexpected behaviors |
| **Adversarial inputs** | Small perturbations can cause dramatic output changes |
| **Context manipulation** | Multi-turn conversations can gradually shift behavior |

### PyRIT: Python Risk Identification Tool

This lab uses [PyRIT](https://github.com/Azure/PyRIT), Microsoft's open-source framework for AI red teaming. PyRIT provides:

- **Orchestrators**: Automated attack strategies (Crescendo, PAIR, Red Teaming)
- **Targets**: Abstractions for HTTP APIs, web UIs, and chat interfaces
- **Scorers**: Automated evaluation of attack success
- **Converters**: Transform prompts to evade detection

---

## 2. Attack Surfaces in AI Applications

When red teaming an AI application, you need to understand **where** to attack. Each layer presents different vulnerabilities:

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (UI)                     │
│   Web forms, chat widgets, mobile apps                      │
│   Attack via: Playwright browser automation                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│   REST endpoints, GraphQL, WebSocket                        │
│   Attack via: HTTP requests                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent / Orchestration                      │
│   LangChain, Semantic Kernel, custom logic                  │
│   Attack via: Tool manipulation, context injection          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Foundation Model                         │
│   GPT-4, Claude, Llama, Mistral                            │
│   Attack via: Prompt injection, jailbreaks                  │
└─────────────────────────────────────────────────────────────┘
```

### The Foundation Model

The underlying LLM (GPT-4, Claude, etc.) is vulnerable to:
- Jailbreaking (bypassing safety training)
- Prompt leaking (extracting system prompts)
- Training data extraction

### The Agent Layer

Code that orchestrates model calls, tools, and memory. Vulnerabilities include:
- Tool abuse (making the agent call unintended functions)
- Memory poisoning (injecting malicious context)
- Goal hijacking (redirecting agent objectives)

### The API Layer

REST endpoints that accept user input. Vulnerabilities include:
- Input validation bypass
- Conversation ID manipulation
- Authentication weaknesses

### The User Interface

Web pages, mobile apps, chat widgets. Vulnerabilities include:
- Client-side prompt construction issues
- Session manipulation
- Different validation than backend

---

## 3. Lab Setup

This lab setup has two parts:
1. **Choose your environment** - Pick one setup method (A, B, or C)
2. **Configure Azure OpenAI** - Common step for all methods

### Prerequisites

- **Git** - For cloning the repository
- **Azure OpenAI** - API access with a GPT-4 or GPT-4o deployment
- Choose **one** development environment below

### Environment Setup Options

| Method | Best For | Requirements | Setup Time |
|--------|----------|--------------|------------|
| **A: DevContainer** ✅ | Most developers | VS Code + Docker Desktop | 5-10 min |
| **B: Codespaces** | Quick trials, remote work | GitHub account | 3-5 min |
| **C: Manual Python** | Advanced users, no Docker | Python 3.11+ | 10-15 min |

---

### Option A: DevContainer (Recommended)

**Benefits:** Consistent environment, pre-configured dependencies, fast local iteration

**1. Install Prerequisites**

- [Docker Desktop](https://docker.com/products/docker-desktop) - Ensure it's running
- [Visual Studio Code](https://code.visualstudio.com/)
- Dev Containers extension (Install from VS Code: `Ctrl+Shift+X` → search "Dev Containers")

**2. Clone and Open**

```bash
git clone https://github.com/yelghali/genai-red-teaming-accelerator.git
cd genai-red-teaming-accelerator
code .
```

**3. Reopen in Container**

Click **"Reopen in Container"** when prompted, or press `F1` → "Dev Containers: Reopen in Container"

First build takes 5-10 minutes and installs:
- Python 3.11, PyRIT 0.8.1, Playwright, Jupyter
- All dependencies from `requirements.txt`
- VS Code extensions for Python/Jupyter

**4. Verify Installation**

Open terminal in VS Code (`Ctrl+``) and run:

```bash
python --version  # Should show Python 3.11.x
python -c "import pyrit; print(f'PyRIT {pyrit.__version__}')"  # Should show 0.8.1
playwright --version  # Should show version 1.x
```

---

### Option B: GitHub Codespaces

**Benefits:** Zero local setup, works anywhere with internet

**Steps:**

1. Go to [github.com/yelghali/genai-red-teaming-accelerator](https://github.com/yelghali/genai-red-teaming-accelerator)
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait 3-5 minutes for automatic setup

Same environment as DevContainer, but runs in the cloud. Includes 60 free hours/month.

---

### Option C: Manual Python Setup

**Benefits:** Full control, no Docker required

```bash
# 1. Clone repository
git clone https://github.com/yelghali/genai-red-teaming-accelerator.git
cd genai-red-teaming-accelerator

# 2. Create virtual environment
python3.11 -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium

# 4. (Optional) Jupyter kernel
python -m ipykernel install --user --name=pyrit_kernel
```

---

### Configure Azure OpenAI (All Options)

**This step is required regardless of which environment option you chose.**

**1. Copy the environment template**

```bash
cp code/.env.example code/.env
```

**2. Get your Azure OpenAI credentials**

Go to [Azure Portal](https://portal.azure.com) → Your Azure OpenAI resource:
- Click **Keys and Endpoint** → Copy **KEY 1** and **Endpoint**
- Click **Model deployments** → Note your deployment name (e.g., `gpt-4o`)

**3. Edit `code/.env` with your values**

```env
# Full chat endpoint URL
OPENAI_CHAT_ENDPOINT="https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions"

# API key from Azure Portal
OPENAI_CHAT_API_KEY="your-api-key-here"

# Deployment name
OPENAI_CHAT_MODEL="gpt-4o"

# Base endpoint (no /openai/deployments path)
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"

# API version
AZURE_OPENAI_API_VERSION="2025-01-01-preview"
```

**4. Verify configuration**

```bash
python --version  # Should be 3.11+
python -c "import pyrit; print(f'✓ PyRIT {pyrit.__version__}')"
python -c "
from dotenv import load_dotenv
import os
load_dotenv('code/.env')
required = ['OPENAI_CHAT_ENDPOINT', 'OPENAI_CHAT_API_KEY', 'OPENAI_CHAT_MODEL']
missing = [v for v in required if not os.getenv(v)]
print('✓ All environment variables configured' if not missing else f'✗ Missing: {missing}')
"
```

**Expected output:**
```
Python 3.11.x
✓ PyRIT 0.8.1
✓ All environment variables configured
```

---

## 4. Module 1: Demo Target Applications

This lab includes two demo applications that simulate real AI chatbots. These provide safe, local targets for testing.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Demo Target Apps                         │
├─────────────────────────────┬───────────────────────────────┤
│   HTTP API (FastAPI)        │   Web UI (Flask)              │
│   Port 8000                 │   Port 5000                   │
│                             │                               │
│   POST /chat                │   Browser-based chat          │
│   - user_prompt             │   - #message-input            │
│   - conversation_id         │   - #send-button              │
│                             │   - .bot-message              │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Azure OpenAI      │
                    │   (GPT-4)           │
                    └─────────────────────┘
```

### Start the Demo Apps

```bash
cd code/demo_target_apps
python run_demo_apps.py
```

**Expected output:**

```
✓ Loaded environment from: /workspaces/genai-red-teaming-accelerator/code/.env
Starting HTTP API demo on http://0.0.0.0:8000
Starting Playwright Web demo on http://0.0.0.0:5000

============================================================
Demo Target Applications Running:
  HTTP API:        http://localhost:8000
  Playwright Web:  http://localhost:5000
============================================================

Press Ctrl+C to stop both applications
```

### HTTP API Target (`http_api_app.py`)

The HTTP API exposes a `/chat` endpoint:

```python
# From code/demo_target_apps/http_api_app.py

class PromptRequest(BaseModel):
    user_prompt: str
    conversation_id: str

@app.post("/chat")
async def chat(req: PromptRequest):
    # Load conversation history
    conversations = load_conversations()
    conv = conversations.get(req.conversation_id, [])
    conv.append({"role": "user", "content": req.user_prompt})
    
    # Call Azure OpenAI
    response = azure_openai_client.chat.completions.create(
        model=os.getenv('OPENAI_CHAT_MODEL'),
        messages=conv,
        max_tokens=1000,
        temperature=0.7
    )
    
    return json.loads(response.to_json())
```

**Test with curl:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Hello!", "conversation_id": "test-123"}'
```

### Web UI Target (`playwright_web_app.py`)

The Web UI provides a browser-based chat interface:

```python
# From code/demo_target_apps/playwright_web_app.py

HTML_TEMPLATE = """
<div id="chat-container"></div>
<div id="input-container">
    <input type="text" id="message-input" placeholder="Type your message...">
    <button id="send-button">Send</button>
</div>
"""

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json.get('message', '')
    
    # Call Azure OpenAI
    response = azure_openai_client.chat.completions.create(
        model=os.getenv('OPENAI_CHAT_MODEL'),
        messages=conversations[session_id],
        max_tokens=1000
    )
    
    return jsonify({"response": response.choices[0].message.content})
```

**Test in browser:** Open http://localhost:5000

![Web UI Demo](assets/web-ui-demo.png)
*The Flask-based web chatbot interface*

---

## 5. Module 2: Interactive Notebooks

Interactive notebooks let you learn PyRIT concepts step-by-step.

### Why Start with Notebooks?

- **Immediate feedback**: See results of each cell
- **Experimentation**: Modify prompts and observe changes
- **Understanding**: Learn how orchestrators work before automating

### Notebook 1: HTTP API Target

**File:** `code/notebooks/api_target.ipynb`

This notebook teaches you to:
1. Configure `HTTPTarget` for REST APIs
2. Send prompts using `PromptSendingOrchestrator`
3. Parse JSON responses

**Key code from the notebook:**

```python
# Initialize PyRIT
from pyrit.common import IN_MEMORY, initialize_pyrit
from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.prompt_target import HTTPTarget, get_http_target_json_response_callback_function

initialize_pyrit(memory_db_type=IN_MEMORY)

# Define the HTTP request template
raw_http_request = """
POST http://127.0.0.1:8000/chat
Content-Type: application/json

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "notebook-test"
}
"""

# Create parsing function for Azure OpenAI response format
parsing_function = get_http_target_json_response_callback_function(
    key="choices[0].message.content"
)

# Create HTTP target
http_target = HTTPTarget(
    http_request=raw_http_request,
    callback_function=parsing_function
)

# Create orchestrator and send prompts
orchestrator = PromptSendingOrchestrator(objective_target=http_target)
response = await orchestrator.send_prompts_async(
    prompt_list=["Tell me a joke about programming"]
)
await orchestrator.print_conversations_async()
```

### Notebook 2: Playwright Target

**File:** `code/notebooks/playwright_target.ipynb`

This notebook teaches you to:
1. Automate browser interactions with Playwright
2. Define interaction functions for web apps
3. Test UI-specific behaviors

**Key code from the notebook:**

```python
from playwright.async_api import Page, async_playwright
from pyrit.models import PromptRequestPiece
from pyrit.prompt_target import PlaywrightTarget

async def interact_with_my_app(page: Page, request_piece: PromptRequestPiece) -> str:
    """
    Interaction function for the demo web chatbot.
    """
    # Define CSS selectors for UI elements
    input_selector = "#message-input"
    send_button_selector = "#send-button"
    bot_message_selector = ".bot-message"

    # Count existing messages to detect new responses
    initial_messages = await page.query_selector_all(bot_message_selector)
    initial_count = len(initial_messages)

    # Fill input and click send
    await page.fill(input_selector, request_piece.converted_value)
    await page.click(send_button_selector)

    # Wait for new bot message
    await page.wait_for_function(
        f"document.querySelectorAll('{bot_message_selector}').length > {initial_count}"
    )

    # Extract and return response
    bot_element = await page.query_selector(f"{bot_message_selector}:last-child")
    return await bot_element.text_content()

# Create Playwright target
playwright_target = PlaywrightTarget(
    interaction_func=interact_with_my_app,
    page=page  # Playwright page object
)
```

### Orchestrator Types

PyRIT provides different attack strategies through orchestrators:

| Orchestrator | Strategy | Use Case |
|-------------|----------|----------|
| `PromptSendingOrchestrator` | Send single prompts | Basic testing, smoke tests |
| `CrescendoOrchestrator` | Gradual escalation | Bypass guardrails through conversation |
| `PAIROrchestrator` | Iterative refinement | Persistent jailbreak attempts |
| `RedTeamingOrchestrator` | Goal-based with scoring | Comprehensive evaluation |

---

## 6. Module 3: Non-Interactive Scanning

After learning with notebooks, use automated scans for repeatable testing.

### The Configuration File

**File:** `code/scan/config.py`

```python
# From code/scan/config.py

# ============================================================================
# TARGET CONFIGURATION
# ============================================================================

# Target type: "http", "playwright", or "both"
TARGET_TYPE = "both"

# ============================================================================
# HTTP TARGET CONFIGURATION
# ============================================================================

RAW_HTTP_REQUEST = """
POST http://127.0.0.1:8000/chat
Content-Type: application/json

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

RESPONSE_JSON_PATH = "choices[0].message.content"
HTTP_TIMEOUT = 20.0

# ============================================================================
# PLAYWRIGHT TARGET CONFIGURATION
# ============================================================================

PLAYWRIGHT_URL = "http://127.0.0.1:5000"
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_INPUT_SELECTOR = "#message-input"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "#send-button"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".bot-message"

# ============================================================================
# ORCHESTRATOR SELECTION
# ============================================================================

# Options: "prompt_sending", "red_teaming", "pair", "crescendo"
# Can be a single value or list: ["crescendo", "pair"]
ORCHESTRATOR = "crescendo"
```

### The Scan Script

**File:** `code/scan/run_pyrit_scan.py`

The scan script:
1. Loads configuration from `config.py`
2. Initializes PyRIT with Azure OpenAI
3. Creates targets based on `TARGET_TYPE`
4. Runs selected orchestrator(s)
5. Prints conversation results

**Key functions:**

```python
# From code/scan/run_pyrit_scan.py

async def run_crescendo_orchestrator(conversation_objective: str, target_type: str, page: Page = None):
    """Run Crescendo orchestrator with specified target"""
    adversarial_chat = create_openai_target()
    scoring_target = create_openai_target()
    objective_target = get_target("CrescendoOrchestrator", target_type, page)
    
    crescendo_orchestrator = CrescendoOrchestrator(
        objective_target=objective_target,
        adversarial_chat=adversarial_chat,
        scoring_target=scoring_target,
        max_backtracks=3,
        prompt_converters=[EmojiConverter()],
        verbose=False,
    )
    
    result = await crescendo_orchestrator.run_attack_async(objective=conversation_objective)
    await result.print_conversation_async()

async def main():
    """Main function to run different orchestrators"""
    initialize_environment()
    
    # Determine targets and orchestrators from config
    orchestrators = config.ORCHESTRATOR if isinstance(config.ORCHESTRATOR, list) else [config.ORCHESTRATOR]
    
    for orchestrator in orchestrators:
        for target_type in targets_to_run:
            if target_type == "playwright":
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
                    page = await browser.new_page()
                    await page.goto(config.PLAYWRIGHT_URL)
                    await run_selected_orchestrator(orchestrator, "playwright", page)
            else:
                await run_selected_orchestrator(orchestrator, "http")
```

### Running the Scan

Make sure demo apps are running first, then:

```bash
cd code/scan
python run_pyrit_scan.py
```

**Expected output:**

```
OPENAI_CHAT_ENDPOINT: https://your-resource.openai.azure.com/...
OPENAI_CHAT_API_KEY: abc123...
OPENAI_CHAT_MODEL: gpt-4o
AZURE_ENDPOINT: https://your-resource.openai.azure.com/
API_VERSION: 2025-01-01-preview

Target Type: both
Selected Orchestrator(s): crescendo

=== Running Crescendo on HTTP target ===

[Conversation output showing attack attempts and responses...]

=== Running Crescendo on PLAYWRIGHT target ===

Launching browser for http://127.0.0.1:5000...
[Conversation output...]

=== All scans completed ===
```

---

## Red Teaming Your Own Application

This section explains how to configure the scanner to test **your own AI application** instead of the demo apps.

### Step 1: Identify Your Target Type

First, determine how users interact with your AI application:

| If your app has... | Use target type | Example |
|-------------------|-----------------|----------|
| REST API endpoint | `http` | `/api/chat`, `/v1/completions` |
| Web chat interface | `playwright` | Chat widget, web form |
| Both API and UI | `both` | Full-stack testing |

### Step 2: Configure `config.py` for HTTP API Target

Edit `code/scan/config.py` to match your API's request/response format.

**Example 1: Simple Chat API**

```python
# code/scan/config.py

TARGET_TYPE = "http"

RAW_HTTP_REQUEST = """
POST https://your-api.example.com/chat
Content-Type: application/json

{
    "message": "{PROMPT}",
    "session_id": "{CONVERSATION_ID}"
}
"""

# Path to extract the response text from your API's JSON response
RESPONSE_JSON_PATH = "response"  # If response is {"response": "Hello!"}
```

**Example 2: OpenAI-Compatible API**

```python
RAW_HTTP_REQUEST = """
POST https://your-api.example.com/v1/chat/completions
Authorization: Bearer your-api-key
Content-Type: application/json

{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "{PROMPT}"}]
}
"""

RESPONSE_JSON_PATH = "choices[0].message.content"
```

**Example 3: API with Custom Headers**

```python
RAW_HTTP_REQUEST = """
POST https://your-api.example.com/api/assistant
Authorization: Bearer {API_KEY}
X-Custom-Header: some-value
Content-Type: application/json

{
    "query": "{PROMPT}",
    "context": {"conversation_id": "{CONVERSATION_ID}"}
}
"""

RESPONSE_JSON_PATH = "data.answer"
```

**Understanding `RESPONSE_JSON_PATH`:**

This tells the scanner where to find the AI's response in your API's JSON output:

| Your API returns | Set `RESPONSE_JSON_PATH` to |
|-----------------|-----------------------------|
| `{"response": "Hello"}` | `"response"` |
| `{"data": {"text": "Hello"}}` | `"data.text"` |
| `{"choices": [{"message": {"content": "Hello"}}]}` | `"choices[0].message.content"` |
| `{"result": ["Hello", "World"]}` | `"result[0]"` |

### Step 3: Configure `config.py` for Web UI Target (Playwright)

To test a web-based chat interface, you need to identify the CSS selectors for:
1. The text input field
2. The send/submit button
3. The bot's response messages

**How to find CSS selectors:**
1. Open your web app in Chrome/Edge
2. Right-click on the input field → **Inspect**
3. Look for `id`, `class`, or other attributes
4. Build a CSS selector (e.g., `#message-input`, `.chat-input`, `textarea[name='prompt']`)

```python
# code/scan/config.py

TARGET_TYPE = "playwright"

# URL of your web application
PLAYWRIGHT_URL = "https://your-app.example.com/chat"

# Run browser without visible window (set False for debugging)
PLAYWRIGHT_HEADLESS = True

# CSS selector for the text input field
# Examples: "#message", ".chat-input", "textarea[placeholder='Ask me anything']"
PLAYWRIGHT_INPUT_SELECTOR = "#chat-input"

# CSS selector for the send button
# Examples: "#send", ".submit-btn", "button[type='submit']"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "button.send"

# CSS selector for bot/assistant messages
# Examples: ".bot-message", ".assistant-response", "div[data-role='assistant']"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".assistant-message"
```

**Debugging Playwright selectors:**

Set `PLAYWRIGHT_HEADLESS = False` to see the browser and verify selectors work correctly.

### Step 4: Choose Your Attack Strategy

Select the orchestrator based on your testing goals:

```python
# code/scan/config.py

# For quick smoke tests (single prompts)
ORCHESTRATOR = "prompt_sending"

# For testing guardrail bypass (recommended for most cases)
ORCHESTRATOR = "crescendo"

# For persistent jailbreak attempts
ORCHESTRATOR = "pair"

# For goal-based attacks with scoring
ORCHESTRATOR = "red_teaming"

# Run multiple strategies
ORCHESTRATOR = ["crescendo", "pair"]
```

| Orchestrator | Turns | Strategy | Best For |
|-------------|-------|----------|----------|
| `prompt_sending` | 1 | Direct prompt | Quick validation |
| `crescendo` | 3-10 | Gradual escalation | Bypassing guardrails |
| `pair` | 5-20 | Iterative refinement | Finding jailbreaks |
| `red_teaming` | 5-15 | Goal-directed | Comprehensive testing |

### Step 5: Run the Scan Locally

```bash
cd code/scan
python run_pyrit_scan.py
```

### Complete `config.py` Example for Your App

Here's a complete configuration example:

```python
# code/scan/config.py - Example for testing your own app

import os
import dotenv
from pathlib import Path

# Load credentials
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)

# Azure OpenAI (for PyRIT's attack generation)
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')

# ============================================================================
# YOUR APPLICATION CONFIGURATION
# ============================================================================

# What to test: "http", "playwright", or "both"
TARGET_TYPE = "http"

# Attack strategy: "prompt_sending", "crescendo", "pair", "red_teaming"
ORCHESTRATOR = "crescendo"

# ============================================================================
# HTTP API CONFIGURATION (if TARGET_TYPE is "http" or "both")
# ============================================================================

RAW_HTTP_REQUEST = """
POST https://my-chatbot-api.azurewebsites.net/api/chat
Content-Type: application/json
Authorization: Bearer my-api-key

{
    "user_message": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

RESPONSE_JSON_PATH = "assistant_response"
HTTP_TIMEOUT = 30.0
USE_TLS = True  # Set True for HTTPS endpoints

# ============================================================================
# WEB UI CONFIGURATION (if TARGET_TYPE is "playwright" or "both")
# ============================================================================

PLAYWRIGHT_URL = "https://my-chatbot.azurewebsites.net"
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_INPUT_SELECTOR = "#user-input"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "#submit-btn"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".bot-response"

# ============================================================================
# SCORING CONFIGURATION
# ============================================================================

SCORER_YAML_PATH = "./scorers/check_fraud_classifier.yaml"
LOG_LEVEL = "WARNING"
```

---

## 7. Module 4: Dockerized (non interactive) Scanning

Run scans in an isolated Docker container for consistency and portability.

### The Dockerfile

**File:** `Dockerfile.pyrit-scan`

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-liberation \
    libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libxshmfence1 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-scan.txt .
RUN pip install --no-cache-dir -r requirements-scan.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy scan script
COPY code/scan/run_pyrit_scan.py /app/code/scan/

# Config and .env are mounted at runtime
WORKDIR /app/code/scan
CMD ["python", "run_pyrit_scan.py"]
```

### The Docker Runner Script

**File:** `run-docker-scan.sh`

```bash
#!/bin/bash
set -e

echo "=== PyRIT Scan Docker Runner ==="

# Check prerequisites
if [ ! -f "code/.env" ]; then
    echo "Error: code/.env file not found!"
    exit 1
fi

# Create results directory
mkdir -p results

# Build Docker image
echo "Building Docker image..."
docker build -f Dockerfile.pyrit-scan -t pyrit-scanner .

# Run container with mounted config and credentials
echo "Running PyRIT scan..."
docker run \
    --rm \
    --name pyrit-scan-$(date +%s) \
    -v $(pwd)/code/.env:/app/code/.env:ro \
    -v $(pwd)/code/scan/config.py:/app/code/scan/config.py:ro \
    -v $(pwd)/code/scan/scorers:/app/code/scan/scorers:ro \
    -v $(pwd)/results:/app/results \
    pyrit-scanner

echo "=== Scan completed ==="
echo "Results saved to: $(pwd)/results"
```

### Running the Dockerized Scan

```bash
# From repository root
./run-docker-scan.sh
```

**Expected output:**

```
=== PyRIT Scan Docker Runner ===
Building Docker image...
[Docker build output...]
Running PyRIT scan...
OPENAI_CHAT_ENDPOINT: https://...
[Scan output...]
=== Scan completed ===
Results saved to: /workspaces/genai-red-teaming-accelerator/results
```

### When to Use Docker

| Scenario | Use Docker? |
|----------|-------------|
| Local development | Optional |
| CI/CD pipelines | Recommended |
| Team standardization | Recommended |
| Production scans | Required |
| Quick experimentation | No (use notebooks) |

### Scanning Your Own App with Docker

To scan your own application using Docker:

**Step 1:** Configure `code/scan/config.py` for your target (see "Red Teaming Your Own Application" section above)

**Step 2:** Ensure your `.env` file has Azure OpenAI credentials:

```bash
# Verify .env exists
cat code/.env
```

**Step 3:** Run the Docker scan:

```bash
./run-docker-scan.sh
```

**Step 4:** If your target is not publicly accessible (e.g., localhost), you need to use Docker networking:

```bash
# For targets running on your host machine
docker run \
    --rm \
    --network="host" \
    -v $(pwd)/code/.env:/app/code/.env:ro \
    -v $(pwd)/code/scan/config.py:/app/code/scan/config.py:ro \
    -v $(pwd)/code/scan/scorers:/app/code/scan/scorers:ro \
    pyrit-scanner
```

**Troubleshooting Docker scans:**

| Issue | Solution |
|-------|----------|
| Can't reach localhost target | Use `--network="host"` or use your machine's IP |
| SSL certificate errors | Set `USE_TLS = False` in config.py or add CA certs |
| Timeout errors | Increase `HTTP_TIMEOUT` in config.py |
| Playwright fails | Ensure target URL is accessible from container |

---

## 8. Module 5: GitHub Actions Integration

Automate security scans in your CI/CD pipeline.

### GitHub Action Definition

**File:** `action.yml`

```yaml
name: 'PyRIT Security Scan'
description: 'Run AI security testing scans using PyRIT framework'
author: 'Microsoft'

inputs:
  azure-openai-endpoint:
    description: 'Azure OpenAI endpoint'
    required: true
  azure-openai-key:
    description: 'Azure OpenAI API key'
    required: true
  azure-openai-deployment:
    description: 'Azure OpenAI deployment/model name'
    required: true

runs:
  using: 'composite'
  steps:
    - name: Display configuration
      shell: bash
      run: |
        echo "PyRIT Scan Configuration:"
        cat code/scan/config.py
    
    - name: Create .env file
      shell: bash
      run: |
        cat > code/scan/.env << 'EOF'
        OPENAI_CHAT_ENDPOINT=${{ inputs.azure-openai-endpoint }}/openai/deployments/${{ inputs.azure-openai-deployment }}/chat/completions
        OPENAI_CHAT_API_KEY=${{ inputs.azure-openai-key }}
        OPENAI_CHAT_MODEL=${{ inputs.azure-openai-deployment }}
        AZURE_OPENAI_ENDPOINT=${{ inputs.azure-openai-endpoint }}/
        AZURE_OPENAI_API_VERSION=2025-01-01-preview
        EOF
    
    - name: Build Docker image
      shell: bash
      run: docker build -f Dockerfile.pyrit-scan -t pyrit-scanner .
    
    - name: Run PyRIT scan
      shell: bash
      run: |
        docker run \
          -v $(pwd)/code/scan/config.py:/app/code/scan/config.py:ro \
          -v $(pwd)/code/scan/.env:/app/code/scan/.env:ro \
          -v $(pwd)/code/scan/scorers:/app/code/scan/scorers:ro \
          pyrit-scanner
```

### Workflow File

**File:** `.github/workflows/pyrit-scan.yml`

```yaml
name: PyRIT Security Scan

on:
  workflow_dispatch:  # Manual trigger
  
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  
  push:
    branches: [main]
    paths:
      - 'code/scan/config.py'
      - 'code/scan/run_pyrit_scan.py'
      - 'code/scan/scorers/**'

jobs:
  pyrit-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Run PyRIT Security Scan
        uses: ./
        with:
          azure-openai-endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          azure-openai-key: ${{ secrets.AZURE_OPENAI_KEY }}
          azure-openai-deployment: ${{ secrets.AZURE_OPENAI_DEPLOYMENT }}
      
      - name: Upload scan results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pyrit-scan-results-${{ github.run_number }}
          path: |
            scan_output.log
            results/
          retention-days: 30
      
      - name: Create scan summary
        if: always()
        run: |
          echo "## PyRIT Security Scan Results" >> $GITHUB_STEP_SUMMARY
          echo "**Run:** ${{ github.run_number }}" >> $GITHUB_STEP_SUMMARY
          echo "**Time:** $(date -u)" >> $GITHUB_STEP_SUMMARY
```

### Setting Up GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value |
|-------------|-------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_KEY` | Your API key |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` (your deployment name) |

### Configuring for Your Target Application

Before using the GitHub Action, update `config.py` with your production target:

```python
# code/scan/config.py

TARGET_TYPE = "http"  # or "playwright" or "both"

RAW_HTTP_REQUEST = """
POST https://your-production-api.example.com/chat
Authorization: Bearer {API_KEY}
Content-Type: application/json

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

ORCHESTRATOR = "crescendo"
```

Commit the configuration:

```bash
git add code/scan/config.py
git commit -m "Configure PyRIT scan for production API"
git push
```

### Running the Workflow

**Manual trigger:**
1. Go to **Actions** tab in GitHub
2. Select **PyRIT Security Scan**
3. Click **Run workflow**

**Automatic triggers:**
- Pushes to `code/scan/` files
- Daily at 2 AM UTC

### Viewing Results

1. Go to **Actions** tab
2. Click on the workflow run
3. View logs for scan output
4. Download artifacts for detailed results

### Scanning Your Own App with GitHub Actions

To integrate PyRIT scanning into your own application's CI/CD:

**Option 1: Use as a Reusable Action**

Reference this action in your workflow:

```yaml
# .github/workflows/security-scan.yml in YOUR repository

name: AI Security Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 3 * * *'  # Daily at 3 AM

jobs:
  red-team-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Clone the red teaming accelerator
      - name: Clone PyRIT Scanner
        run: |
          git clone https://github.com/yelghali/genai-red-teaming-accelerator.git scanner
      
      # Copy your custom config
      - name: Configure scan
        run: |
          cp my-app-config.py scanner/code/scan/config.py
      
      # Run the scan
      - name: Run PyRIT Scan
        uses: ./scanner
        with:
          azure-openai-endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          azure-openai-key: ${{ secrets.AZURE_OPENAI_KEY }}
          azure-openai-deployment: ${{ secrets.AZURE_OPENAI_DEPLOYMENT }}
      
      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: security-scan-results
          path: scanner/results/
```

**Option 2: Fork and Customize**

1. Fork this repository to your organization
2. Modify `code/scan/config.py` with your target configuration
3. Add GitHub secrets for Azure OpenAI
4. The workflow will run automatically

**Option 3: Add Scan to Existing Pipeline**

Add to your existing deployment workflow:

```yaml
# In your existing workflow

jobs:
  deploy:
    # ... your deployment steps ...
  
  security-scan:
    needs: deploy  # Run after deployment
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: yelghali/genai-red-teaming-accelerator
      
      - name: Configure for staging environment
        run: |
          cat > code/scan/config.py << 'EOF'
          import os
          import dotenv
          from pathlib import Path
          
          env_path = Path(__file__).parent.parent / '.env'
          if env_path.exists():
              dotenv.load_dotenv(dotenv_path=env_path)
          
          AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
          API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')
          
          TARGET_TYPE = "http"
          ORCHESTRATOR = "crescendo"
          
          RAW_HTTP_REQUEST = """
          POST https://my-app-staging.azurewebsites.net/api/chat
          Content-Type: application/json
          
          {
              "prompt": "{PROMPT}",
              "session": "{CONVERSATION_ID}"
          }
          """
          
          RESPONSE_JSON_PATH = "response"
          HTTP_TIMEOUT = 30.0
          USE_TLS = True
          
          SCORER_YAML_PATH = "./scorers/check_fraud_classifier.yaml"
          LOG_LEVEL = "WARNING"
          EOF
      
      - uses: ./
        with:
          azure-openai-endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          azure-openai-key: ${{ secrets.AZURE_OPENAI_KEY }}
          azure-openai-deployment: ${{ secrets.AZURE_OPENAI_DEPLOYMENT }}
```

### Best Practices for CI/CD Integration

| Practice | Recommendation |
|----------|----------------|
| **When to scan** | After deployment to staging/test environment |
| **Frequency** | Daily scheduled + on-demand for releases |
| **Timeout** | Set 60+ minutes for comprehensive scans |
| **Secrets** | Never hardcode credentials in config.py |
| **Results** | Store as artifacts with 30+ day retention |
| **Notifications** | Add Slack/Teams webhook for failures |
| **Blocking** | Start with non-blocking, then enable blocking after baseline |

---

## Troubleshooting

### Demo apps won't start

```bash
# Check if ports are in use
lsof -i :8000
lsof -i :5000

# Kill existing processes
pkill -f "python.*demo"

# Restart
python code/demo_target_apps/run_demo_apps.py
```

### Missing environment variables

```bash
# Verify .env exists
ls -la code/.env

# Check contents (safely)
grep "^[A-Z]" code/.env | head -5

# Copy from example if missing
cp code/.env.example code/.env
```

### Playwright errors on Windows

```python
# Add to your script before asyncio.run()
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

### GitHub Action fails

1. Verify all three secrets are set correctly
2. Check the workflow logs for specific errors
3. Test locally with Docker first: `./run-docker-scan.sh`

---

## Summary

This workshop covered:

| Module | What You Learned |
|--------|-----------------|
| **Concepts** | AI red teaming fundamentals, attack surfaces |
| **Demo Apps** | HTTP API and Web UI targets for testing |
| **Notebooks** | Interactive exploration of PyRIT orchestrators |
| **Scanning** | Automated, non-interactive security testing |
| **Docker** | Containerized, portable scan execution |
| **GitHub Actions** | CI/CD integration for continuous security |

### Next Steps

1. Complete all notebook exercises
2. Configure `config.py` for your own application
3. Set up GitHub Actions in your repository
4. Explore custom scorers and converters
5. Read the [PyRIT documentation](https://github.com/Azure/PyRIT)

### Resources

- [PyRIT GitHub Repository](https://github.com/Azure/PyRIT)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Microsoft AI Red Team](https://www.microsoft.com/security/blog/ai-red-team/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

