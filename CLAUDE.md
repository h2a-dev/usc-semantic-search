# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the USC (United States Code) MCP Server - a semantic search system for US federal law. It uses:
- **VoyageAI embeddings** (voyage-law-2 model) for legal-optimized semantic search
- **ChromaDB** for vector storage and retrieval
- **FastMCP** for exposing search capabilities to AI agents
- **USLM XML parsing** for extracting structured legal text

## Common Development Tasks

### Build and Run the Server
```bash
# Install dependencies (using uv - fast Python package manager)
uv pip install -e ".[dev]"

# Download USC data (example: Title 26 - Tax Code)
python scripts/download_usc.py --title 26

# Process and embed the data
python scripts/process_usc.py --title 26

# Run the MCP server
python -m usc_mcp.server
# OR use the run script
./run_server.sh
```

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=usc_mcp

# Run specific test file
pytest tests/test_parser.py

# Test the running server
python scripts/test_server.py
```

### Lint and Format Code
```bash
# Format code
black usc_mcp scripts tests

# Lint with flake8
flake8 usc_mcp scripts tests

# Lint with ruff (faster)
ruff check usc_mcp scripts tests

# Type checking
mypy usc_mcp
```

## High-Level Architecture

### Core Components

1. **MCP Server (`usc_mcp/server.py`)**: FastMCP server exposing 7 tools:
   - `search_usc`: Semantic search across USC sections
   - `get_citation`: Retrieve specific section by citation
   - `browse_usc`: Navigate USC hierarchy (titles → chapters → sections)
   - `get_context`: Get surrounding sections for context
   - `test_connection`: Health check
   - `get_database_stats`: Database statistics
   - `health_check`: Service status

2. **Database Layer (`usc_mcp/database.py`)**: ChromaDB interface
   - Manages vector storage with persistence
   - Handles metadata filtering and hierarchical queries
   - Supports ~200MB per USC title with <100ms search times

3. **Embedder (`usc_mcp/embedder.py`)**: VoyageAI integration
   - Uses `voyage-law-2` model optimized for legal text
   - Supports batch embedding with retry logic
   - Includes reranking for improved relevance

4. **Parser (`usc_mcp/parser.py`)**: USLM XML parser
   - Extracts structured sections from USC XML files
   - Preserves hierarchical relationships and metadata
   - Handles complex legal document structure (subsections, notes, amendments)

### Data Flow

1. **Download**: USC XML files downloaded from uscode.house.gov
2. **Parse**: USLM parser extracts sections with full metadata
3. **Embed**: VoyageAI generates semantic embeddings for each section
4. **Store**: ChromaDB persists embeddings with metadata
5. **Search**: MCP server handles queries using semantic similarity + reranking

### Key Design Decisions

- **Lazy Initialization**: Server components initialize on first use to handle various startup scenarios
- **Section-Level Granularity**: Each USC section is a separate vector for precise retrieval
- **Legal Citation Formats**: Handles multiple formats (e.g., "26 USC 280A", "26 § 162")
- **Hierarchical Browsing**: Preserves USC structure for navigation
- **Reranking**: Uses VoyageAI's rerank-2 model for better relevance

## Important Configuration

### Environment Variables (in `.env`)
- `VOYAGE_API_KEY`: Required for embeddings
- `CHROMA_PERSIST_DIR`: Database location (default: `./data/db`)
- `USC_DATA_DIR`: XML file location (default: `./data/xml`)

### Performance Considerations
- Batch size: 25 texts per embedding request
- Rate limiting: 0.5s pause between batches
- Database uses absolute paths to work from any directory
- Supports concurrent async operations for better performance

## Common Issues and Solutions

1. **Database not found**: Server uses absolute paths, check `CHROMA_PERSIST_DIR`
2. **Citation not found**: Try multiple formats - the parser handles various USC citation styles
3. **Slow embeddings**: Check batch size and API rate limits
4. **Memory usage**: ~2GB for server + database, scales with number of titles

## Testing and Debugging

- Logs to `~/usc_mcp_debug.log` with DEBUG level
- Database stats available via `get_database_stats()` tool
- Test specific citations with `scripts/test_server.py`
- Check embeddings with `database.export_metadata()`