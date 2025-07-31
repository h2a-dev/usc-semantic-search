#!/bin/bash
# Run the USC MCP Server

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    echo "Please copy .env.example to .env and add your VOYAGE_API_KEY"
    exit 1
fi

# Check if VOYAGE_API_KEY is set
if [ -z "$VOYAGE_API_KEY" ]; then
    echo "Error: VOYAGE_API_KEY not set in .env file"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Or: pip install uv"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "Installing dependencies with uv..."
    uv pip install -r requirements.txt
fi

# Check if database has content
echo "Checking database..."
python -c "from usc_mcp.database import ChromaDatabase; db = ChromaDatabase(); stats = db.get_stats(); print(f'Database contains {stats[\"total_sections\"]} sections')"

if [ $? -ne 0 ]; then
    echo "Warning: Database check failed. You may need to run process_usc.py first."
fi

# Run the server
echo "Starting USC Semantic Search MCP Server..."
python -m usc_mcp.server