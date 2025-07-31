# USC Semantic Search MCP Server

An MCP (Model Context Protocol) server that provides AI-powered semantic search capabilities for the United States Code. Built for legal professionals, researchers, and developers who need intelligent access to federal law.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🌟 Features

- 🔍 **Semantic Search**: Natural language search across all USC titles
- 📚 **Legal-Optimized**: Uses VoyageAI's voyage-law-2 model designed for legal text
- 🚀 **Fast Response**: ChromaDB vector database for <100ms search times
- 🤖 **MCP Integration**: Direct access for AI agents via Model Context Protocol
- 📖 **Full Context**: Preserves hierarchical structure and cross-references
- ⚖️ **Accurate Citations**: Returns proper legal citations for all results
- 🔄 **Reranking**: Advanced relevance scoring for better search results
- 🏗️ **Hierarchical Browse**: Navigate USC structure (titles → chapters → sections)

## 📸 Screenshots

<details>
<summary>Click to see example usage</summary>

```python
# Semantic search example
results = await search_usc("home office tax deduction", limit=5)
# Returns relevant sections like 26 USC 280A with context

# Citation lookup example
section = await get_citation("26 USC 280A")
# Returns full text and metadata for the home office deduction

# Hierarchical browsing
titles = await browse_usc()  # List all USC titles
chapters = await browse_usc(title=26)  # List chapters in Title 26
```

</details>

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd uscode

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
uv pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env and add your VOYAGE_API_KEY

# Download sample USC data
usc-download --title 26

# Process and embed the data
usc-process --title 26

# Start the MCP server
usc-server
```

## 📋 Prerequisites

- Python 3.9+
- [VoyageAI API key](https://www.voyageai.com/) (free tier available)
- 2GB storage per USC title (~50GB for full USC)
- 8GB RAM recommended

### Getting a VoyageAI API Key

1. Sign up at [VoyageAI](https://www.voyageai.com/)
2. Navigate to your [API keys page](https://dash.voyageai.com/)
3. Create a new API key
4. The free tier includes 50M tokens per month

## Installation

### Option 1: Install from GitHub
```bash
# Clone the repository
git clone https://github.com/h2a-dev/usc-semantic-search.git
cd usc-semantic-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

### Option 2: Install with uv (faster)
```bash
# Install uv if you haven't already
pip install uv

# Clone and install
git clone https://github.com/h2a-dev/usc-semantic-search.git
cd usc-semantic-search
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## Architecture

The system consists of:
- **Data Pipeline**: Downloads and processes USC XML files
- **Embedding Engine**: Generates semantic embeddings using VoyageAI
- **Vector Database**: ChromaDB for efficient similarity search
- **MCP Server**: FastMCP server exposing search tools to AI agents

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Usage

### Command Line Tools

After installation, these commands are available:

```bash
# Download USC titles
usc-download --title 26
usc-download --title 26 --title 42
usc-download --all

# Process and embed
usc-process --title 26
usc-process --all --clear  # Clear existing and process all

# Run the server
usc-server

# Test the system
usc-test
```

### For AI Agents

Once the server is running, AI agents can use these tools:

```python
# Search for relevant sections
results = search_usc("tax deductions for home office", limit=5)

# Get specific citation
section = get_citation("26 USC 280A")

# Browse hierarchy
chapters = browse_usc(title=26)

# Get context around a section
context = get_context("26-1-280A", context_size=2)
```

### For Developers

```python
from usc_mcp import USCSearchClient

client = USCSearchClient()
results = client.search("capital gains tax", title=26)
```

## ⚙️ Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your VoyageAI API key:
```env
VOYAGE_API_KEY=your_voyage_api_key_here
```

Other configuration options:
- `VOYAGE_EMBEDDING_MODEL`: Model for embeddings (default: `voyage-law-2`)
- `CHROMA_PERSIST_DIR`: Database location (default: `./data/db`)
- `USC_DATA_DIR`: XML storage (default: `./data/xml`)
- `BATCH_SIZE`: Embedding batch size (default: 25)

## Development

### Setup with uv

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=usc_mcp

# Run specific test
pytest tests/test_parser.py
```

### Code Quality

```bash
# Format code
black usc_mcp scripts tests

# Lint code
flake8 usc_mcp scripts tests
ruff check usc_mcp scripts tests

# Type checking
mypy usc_mcp
```

## 📊 Performance

- **Search Speed**: <100ms for semantic search
- **Embedding Rate**: ~1000 sections/minute
- **Storage**: ~2GB per USC title
- **Memory**: ~2GB for server + database

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [VoyageAI](https://www.voyageai.com/) for their excellent legal embedding models
- [ChromaDB](https://www.trychroma.com/) for the vector database
- [FastMCP](https://github.com/pyramidpy/fastmcp) for the MCP framework
- [uscode.house.gov](https://uscode.house.gov/) for providing USC data

## 📚 Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [VoyageAI Documentation](https://docs.voyageai.com/)

## ⚠️ Disclaimer

This tool is for research and educational purposes. While we strive for accuracy, always verify legal information with official sources and consult qualified legal professionals for legal advice.

## 🐛 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you've installed all dependencies with `pip install -e .`
2. **API Key Error**: Verify your VoyageAI API key is correctly set in `.env`
3. **Database Error**: Ensure the data directory has write permissions
4. **Memory Error**: For full USC, ensure you have at least 8GB RAM available

For more help, please [open an issue](https://github.com/h2a-dev/usc-semantic-search/issues).

---

Made with ❤️ by the USC Semantic Search team