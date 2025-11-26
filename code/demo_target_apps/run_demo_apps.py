"""
Run both demo target applications
Starts HTTP API on port 8000 and Playwright Web on port 5000
"""

import os
import sys
from pathlib import Path
from multiprocessing import Process
import time
import signal
import dotenv

# Load environment variables from code/.env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Please copy code/.env.example to code/.env and configure it")

# Set AZURE_OPENAI_API_KEY for SDK compatibility
if os.getenv('OPENAI_CHAT_API_KEY'):
    os.environ['AZURE_OPENAI_API_KEY'] = os.getenv('OPENAI_CHAT_API_KEY')

def run_http_api():
    """Run HTTP API demo app"""
    print("Starting HTTP API demo on http://0.0.0.0:8000")
    from http_api_app import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def run_playwright_web():
    """Run Playwright web demo app"""
    print("Starting Playwright Web demo on http://0.0.0.0:5000")
    from playwright_web_app import app
    app.run(host='0.0.0.0', port=5000, debug=False)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nShutting down demo applications...")
    sys.exit(0)

if __name__ == "__main__":
    # Verify required environment variables
    required_vars = ['AZURE_OPENAI_ENDPOINT', 'OPENAI_CHAT_API_KEY', 'OPENAI_CHAT_MODEL']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Please set them in your .env file or environment")
        sys.exit(1)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start both applications
    http_process = Process(target=run_http_api)
    web_process = Process(target=run_playwright_web)
    
    http_process.start()
    time.sleep(2)  # Give HTTP API time to start
    web_process.start()
    
    print("\n" + "="*60)
    print("Demo Target Applications Running:")
    print("  HTTP API:        http://localhost:8000")
    print("  Playwright Web:  http://localhost:5000")
    print("="*60)
    print("\nPress Ctrl+C to stop both applications\n")
    
    try:
        http_process.join()
        web_process.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        http_process.terminate()
        web_process.terminate()
        http_process.join()
        web_process.join()
