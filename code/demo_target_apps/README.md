# Demo Target Applications

This directory contains demo target applications for testing PyRIT scans.

## Applications

1. **HTTP API** (`http_api_app.py`) - FastAPI chatbot on port 8000
2. **Playwright Web** (`playwright_web_app.py`) - Flask web interface on port 5000

## Quick Start

### Option 1: Run Locally with Python

```bash
# Prerequisites: Configure environment variables
cp ../code/.env.example ../code/.env
# Edit code/.env with your Azure OpenAI credentials

# The apps will automatically load from code/.env
cd code/demo_target_apps
python run_demo_apps.py
```

Visit:
- HTTP API: http://localhost:8000/docs (Swagger UI)
- Web App: http://localhost:5000

### Option 2: Run with Docker Compose (Recommended)

```bash
cd demo_target_apps

# Copy and configure environment
cp .env.scan.example .env.scan
# Edit .env.scan with your Azure OpenAI credentials

# Start demo apps and run PyRIT scan
docker-compose up

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

## What Docker Compose Does

1. **Builds and starts demo apps** container with both HTTP API and Web app
2. **Waits for apps to be healthy** using health check on port 8000
3. **Runs PyRIT scanner** against both demo apps
4. **Saves results** to `../results/` directory

## Configuration

- **Demo apps config**: Set in `.env.scan` (Azure OpenAI credentials)
- **Scan config**: Use `config.demo.py` or modify `../code/config.py`
  - Set `TARGET_TYPE = "both"` to scan both apps
  - HTTP endpoint: `http://demo-apps:8000/chat` (Docker network)
  - Playwright URL: `http://demo-apps:5000` (Docker network)

## Network Architecture

```
┌─────────────────────────────────────┐
│  demo-apps container                │
│  ├─ HTTP API (port 8000)            │
│  └─ Web App (port 5000)             │
└──────────────┬──────────────────────┘
               │ pyrit-network
┌──────────────▼──────────────────────┐
│  pyrit-scanner container            │
│  Scans both targets                 │
└─────────────────────────────────────┘
```

## Testing Individual Apps

### HTTP API
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Hello!", "conversation_id": "test123"}'
```

### Web App
Open browser to http://localhost:5000 and interact with the chat interface.

## Customizing the Scan

Edit `config.demo.py` to change:
- `ORCHESTRATOR` - Which attack orchestrator to use
- `TARGET_TYPE` - "http", "playwright", or "both"
- Selectors and timeouts

Or mount your own config:
```yaml
volumes:
  - ./my-custom-config.py:/app/code/config.py:ro
```
