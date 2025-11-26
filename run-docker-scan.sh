#!/bin/bash
set -e

echo "=== PyRIT Scan Docker Runner ==="

# Check if .env file exists
if [ ! -f "code/.env" ]; then
    echo "Error: code/.env file not found!"
    echo "Please create it with your Azure OpenAI credentials:"
    echo ""
    echo "cat > code/.env << EOF"
    echo "OPENAI_CHAT_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions"
    echo "OPENAI_CHAT_API_KEY=your-api-key-here"
    echo "OPENAI_CHAT_MODEL=your-deployment-name"
    echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
    echo "AZURE_OPENAI_API_VERSION=2024-02-15-preview"
    echo "EOF"
    exit 1
fi

# Check if config.py exists
if [ ! -f "code/scan/config.py" ]; then
    echo "Warning: code/scan/config.py not found. Using default configuration."
fi

# Create results directory
mkdir -p results

# Build Docker image
echo "Building Docker image..."
docker build -f Dockerfile.pyrit-scan -t pyrit-scanner .

# Run container
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
