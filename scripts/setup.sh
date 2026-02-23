#!/bin/bash
# Setup script for Amazon FBA Agent Crew
set -e

echo "=== Amazon FBA Agent Crew Setup ==="

# Check Python version
python3 --version

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template. Please fill in your API keys."
fi

# Run tests
python -m pytest tests/ -v

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Edit .env with your API keys (SP-API, Anthropic, Firecrawl, Exa)"
echo "2. Run: python src/main.py"
echo "3. Or deploy with: docker compose up -d"
