#!/bin/bash

# Test script to verify Docker setup for PyRIT scans

echo "=== PyRIT Docker Setup Verification ==="
echo ""

# Check Docker installed
echo "1. Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "   ❌ Docker not found. Please install Docker first."
    exit 1
fi
echo "   ✓ Docker found: $(docker --version)"

# Check Docker Compose
echo ""
echo "2. Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "   ❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi
echo "   ✓ Docker Compose found"

# Check Docker running
echo ""
echo "3. Checking Docker daemon..."
if ! docker info &> /dev/null; then
    echo "   ❌ Docker daemon not running. Please start Docker."
    exit 1
fi
echo "   ✓ Docker daemon running"

# Check .env file
echo ""
echo "4. Checking environment file..."
if [ ! -f "code/.env" ]; then
    echo "   ❌ code/.env not found"
    echo ""
    echo "   Create it with:"
    echo "   cp code/.env.example code/.env"
    echo "   # Then edit with your Azure OpenAI credentials"
    exit 1
fi
echo "   ✓ code/.env exists"

# Verify required env vars
echo ""
echo "5. Checking required environment variables..."
source code/.env
missing_vars=0

check_var() {
    if [ -z "${!1}" ]; then
        echo "   ❌ $1 not set in code/.env"
        missing_vars=$((missing_vars + 1))
    else
        echo "   ✓ $1 is set"
    fi
}

check_var "OPENAI_CHAT_ENDPOINT"
check_var "OPENAI_CHAT_API_KEY"
check_var "OPENAI_CHAT_MODEL"
check_var "AZURE_OPENAI_ENDPOINT"
check_var "AZURE_OPENAI_API_VERSION"

if [ $missing_vars -gt 0 ]; then
    echo ""
    echo "   Please set missing variables in code/.env"
    exit 1
fi

# Check config.py
echo ""
echo "6. Checking scan configuration..."
if [ ! -f "code/scan/config.py" ]; then
    echo "   ❌ code/scan/config.py not found"
    exit 1
fi
echo "   ✓ code/scan/config.py exists"

# Check scorers directory
echo ""
echo "7. Checking scorers directory..."
if [ ! -d "code/scan/scorers" ]; then
    echo "   ❌ code/scan/scorers directory not found"
    exit 1
fi
echo "   ✓ code/scan/scorers directory exists"

# Create results directory if needed
echo ""
echo "8. Checking results directory..."
if [ ! -d "results" ]; then
    echo "   ⚠ results directory not found, creating..."
    mkdir -p results
fi
echo "   ✓ results directory ready"

# Summary
echo ""
echo "==================================================="
echo "✅ All checks passed!"
echo "==================================================="
echo ""
echo "You can now run:"
echo ""
echo "  Standalone scanner:  ./run-docker-scan.sh"
echo "  Full stack:          cd code/demo_target_apps && docker-compose up"
echo ""
echo "See DOCKER_GUIDE.md for detailed usage."
