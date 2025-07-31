# USC Semantic Search MCP Server - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
First, install `uv` if you haven't already:
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### 1. Set up environment (one-time setup)
```bash
# Clone the repository
git clone <repository-url>
cd uscode

# Copy environment template
cp .env.example .env

# Edit .env and add your VoyageAI API key
# Get your key at: https://dash.voyageai.com/
nano .env  # or use your favorite editor

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package with all dependencies
uv pip install -e ".[dev]"
```

### 2. Download USC data
```bash
# Download Title 26 (Tax Code) as a sample
usc-download --title 26

# Or download multiple titles
usc-download --title 26 --title 42 --title 15

# Or download sample set (Titles 1, 26, 42)
usc-download --sample

# Or download all titles (warning: ~3GB download)
usc-download --all
```

### 3. Process and embed the data
```bash
# Process Title 26
usc-process --title 26

# This will:
# - Parse the XML files
# - Extract sections and metadata
# - Generate embeddings using VoyageAI
# - Store in ChromaDB
# - Show cost estimates before embedding

# Process multiple titles
usc-process --title 26 --title 42

# Clear database and process all downloaded titles
usc-process --all --clear
```

### 4. Test the system
```bash
# Run the test script
usc-test

# You should see:
# ✓ Database initialized
# ✓ Embedder initialized
# ✓ Tools initialized
# ✓ Database contains X sections
# ✓ Search returned 3 results
```

### 5. Start the MCP server
```bash
# Easy way (using the startup script)
./run_server.sh

# Or using the installed command
usc-server

# Or manually
python -m usc_mcp.server
```

## 📊 Using the MCP Server

Once running, the server exposes these tools to AI agents:

### Search Tool
```python
# Natural language search
search_usc("home office tax deduction", limit=5)
search_usc("capital gains real estate", title=26)
search_usc("medical expense deductions", rerank=True)
```

### Citation Tool
```python
# Get specific sections
get_citation("26 USC 280A")  # Home office deduction
get_citation("26 USC 162")   # Business expenses
get_citation("42 USC 2000e") # Title VII
```

### Browse Tool
```python
# Navigate hierarchy
browse_usc()                    # List all titles
browse_usc(title=26)           # List chapters in Title 26
browse_usc(title=26, chapter=1) # List sections in Chapter 1
```

### Context Tool
```python
# Get surrounding sections
get_context("26-280A", context_size=2)  # 2 sections before/after
get_context("26-162", context_size=5)   # Broader context
```

### Stats Tool
```python
# Check database statistics
get_database_stats()  # Returns sections count, titles, etc.
```

## 🛠️ Troubleshooting

### "VOYAGE_API_KEY not found"
- Make sure you've added your API key to `.env`
- Get a key at https://dash.voyageai.com/
- Check: `echo $VOYAGE_API_KEY` (should show your key)

### "No XML files found"
- Run the download first: `usc-download --title 26`
- Check `data/xml/` directory for downloaded files

### "Database is empty"
- Run the processing script: `usc-process --title 26`
- Check for errors in the console output

### Import errors
- Make sure you're in the virtual environment: `source .venv/bin/activate`
- Reinstall: `uv pip install -e ".[dev]"`

### uv not found
- Install uv first: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Or use pip: `pip install uv`

### Download errors
- Check internet connection
- The USC website may be temporarily unavailable
- Try again with exponential backoff built in

## 📈 Performance Tips

1. **Start small**: Test with Title 26 before processing all USC
2. **Monitor costs**: Check embedding costs in console output (~$0.12 per 1M tokens)
3. **Use reranking**: Set `rerank=True` for better search quality
4. **Batch processing**: System automatically batches 25 texts at a time
5. **Async processing**: Multiple embeddings processed concurrently

## 🔧 Configuration

Key settings in `.env`:
```bash
# VoyageAI
VOYAGE_API_KEY=your_key_here
VOYAGE_EMBEDDING_MODEL=voyage-law-2  # Legal-optimized
VOYAGE_RERANK_MODEL=rerank-2

# Processing
BATCH_SIZE=25                    # Texts per API call
MAX_TOKENS_PER_CHUNK=1000       # Chunk size
CHUNK_OVERLAP=100               # Overlap between chunks

# Storage
CHROMA_PERSIST_DIR=./data/db   # Vector database location
USC_DATA_DIR=./data/xml        # XML files location

# Server
MCP_SERVER_PORT=3000           # MCP server port
```

## 🚄 Why uv?

`uv` is a fast Python package installer that offers:
- **10-100x faster** package installation than pip
- **Better dependency resolution**
- **Built-in virtual environment management**
- **Drop-in replacement** for pip commands

## 📚 Common Workflows

### Add a new USC title
```bash
# Download
usc-download --title 15

# Process
usc-process --title 15

# Verify
usc-test
```

### Update existing title
```bash
# Re-download (will skip if exists)
usc-download --title 26

# Clear and reprocess
usc-process --title 26 --clear
```

### Full USC deployment
```bash
# Download all (3GB+)
usc-download --all

# Process all (may take hours)
usc-process --all

# Monitor
watch -n 5 'echo "Sections:" && sqlite3 data/db/chroma.sqlite3 "SELECT COUNT(*) FROM embeddings"'
```

## 🔍 Example Searches

```python
# Tax-related
"home office deduction requirements"
"capital gains tax rates"
"charitable contribution limits"
"depreciation methods"

# Employment law
"discrimination protected classes"
"FMLA eligibility"
"overtime exemptions"

# Healthcare
"HIPAA privacy requirements"
"Medicare eligibility age"
"ACA employer mandate"
```

## 🆘 Need Help?

- **Logs**: Check console output for detailed errors
- **Docs**: See `README.md`, `ARCHITECTURE.md`, `PROJECT_PLAN.md`
- **Test**: Use `usc-test` to verify components
- **Database**: Check `data/db/` for ChromaDB files
- **Support**: Open an issue on GitHub

## ⚡ Quick Commands Reference

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Download & Process
usc-download --title 26
usc-process --title 26

# Run
usc-server

# Test
usc-test
```