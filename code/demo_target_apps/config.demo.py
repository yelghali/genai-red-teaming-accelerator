"""
Demo configuration for PyRIT scan
Configured to scan the demo target applications running in Docker
"""

import os
import dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)

# ============================================================================
# AZURE OPENAI CONFIGURATION (from .env)
# ============================================================================

AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')

# ============================================================================
# TARGET CONFIGURATION
# ============================================================================

# Target type: "http", "playwright", or "both"
TARGET_TYPE = "both"

# ============================================================================
# HTTP TARGET CONFIGURATION
# ============================================================================

# HTTP Request template for the demo API (runs on port 8000 in Docker)
RAW_HTTP_REQUEST = """
POST http://demo-apps:8000/chat
Content-Type: application/json

{
    "user_prompt": "{PROMPT}",
    "conversation_id": "{CONVERSATION_ID}"
}
"""

# JSON path to extract the response content from the API response
RESPONSE_JSON_PATH = "choices[0].message.content"

# Timeout for HTTP requests (in seconds)
HTTP_TIMEOUT = 20.0

# Whether to use TLS for HTTP requests
USE_TLS = False

# ============================================================================
# PLAYWRIGHT TARGET CONFIGURATION
# ============================================================================

# URL of the Playwright demo web app (runs on port 5000 in Docker)
PLAYWRIGHT_URL = "http://demo-apps:5000"

# Whether to run Playwright browser in headless mode
PLAYWRIGHT_HEADLESS = True

# Playwright selectors for the demo web app
PLAYWRIGHT_INPUT_SELECTOR = "#message-input"
PLAYWRIGHT_SEND_BUTTON_SELECTOR = "#send-button"
PLAYWRIGHT_BOT_MESSAGE_SELECTOR = ".bot-message"

# ============================================================================
# GENERAL CONFIGURATION
# ============================================================================

SCORER_YAML_PATH = "./scorers/check_fraud_classifier.yaml"
LOG_LEVEL = "WARNING"

# ============================================================================
# ORCHESTRATOR SELECTION
# ============================================================================

# Select which orchestrator(s) to run
# Options: "prompt_sending", "red_teaming", "pair", "crescendo"
# Can be a single value or a list: e.g., ["crescendo", "pair"]
ORCHESTRATOR = "crescendo"
