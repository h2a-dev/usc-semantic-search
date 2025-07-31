# United States Code Semantic Search MCP Server - Project Plan

## Project Overview
Build a FastMCP server that provides semantic search capabilities for the United States Code using VoyageAI embeddings.

## Architecture Overview
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  USC XML Files  │ --> │  Text Extractor  │ --> │ VoyageAI        │
│  (uscode.house) │     │  & Processor     │     │ Embeddings      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                            │
                                                            v
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AI Agents      │ <-- │  FastMCP Server  │ <-- │ Vector Database │
│                 │     │  (Search Tools)  │     │ (ChromaDB)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Phase 1: Setup & Infrastructure (Week 1)
### 1.1 Project Setup
- [ ] Initialize Python project with proper structure
- [ ] Set up virtual environment
- [ ] Install dependencies (FastMCP, VoyageAI, ChromaDB, lxml, etc.)
- [ ] Configure .env file with VoyageAI API key
- [ ] Create project structure

### 1.2 Data Download Module
- [ ] Create USC downloader script
- [ ] Implement rate limiting and error handling
- [ ] Download sample USC title (Title 26 - Tax Code recommended)
- [ ] Set up storage structure for XML files

## Phase 2: Data Processing (Week 1-2)
### 2.1 XML Parser
- [ ] Implement USLM XML parser using lxml
- [ ] Extract hierarchical structure (titles, chapters, sections)
- [ ] Extract text content preserving context
- [ ] Handle metadata (citations, notes, references)

### 2.2 Text Processing
- [ ] Implement text chunking strategy (section-based)
- [ ] Preserve hierarchical context in chunks
- [ ] Create metadata for each chunk (title, chapter, section, etc.)
- [ ] Implement batch processing for large files

## Phase 3: Embedding & Storage (Week 2)
### 3.1 VoyageAI Integration
- [ ] Set up VoyageAI client
- [ ] Implement embedding generation with voyage-law-2 model
- [ ] Handle rate limiting and API errors
- [ ] Implement batch embedding processing

### 3.2 Vector Database Setup
- [ ] Set up ChromaDB for vector storage
- [ ] Design collection schema
- [ ] Implement upsert functionality
- [ ] Create indices for efficient retrieval

## Phase 4: FastMCP Server (Week 3)
### 4.1 Server Setup
- [ ] Create FastMCP server structure
- [ ] Implement basic health check tool
- [ ] Set up logging and error handling

### 4.2 Search Tools
- [ ] Implement semantic search tool
- [ ] Implement citation lookup tool
- [ ] Implement hierarchical browse tool
- [ ] Add context retrieval for search results

### 4.3 Advanced Features
- [ ] Implement reranking with voyage-rerank-2
- [ ] Add filtering by title/chapter/section
- [ ] Implement cross-reference resolution

## Phase 5: Testing & Optimization (Week 3-4)
### 5.1 Testing
- [ ] Unit tests for all components
- [ ] Integration tests for MCP server
- [ ] Performance testing with large datasets
- [ ] Search quality evaluation

### 5.2 Optimization
- [ ] Optimize embedding batch sizes
- [ ] Implement caching for frequent queries
- [ ] Optimize vector database queries
- [ ] Memory usage optimization

## Phase 6: Full USC Deployment (Week 4)
### 6.1 Full Download
- [ ] Download all USC titles
- [ ] Process and embed all content
- [ ] Monitor resource usage

### 6.2 Production Setup
- [ ] Set up monitoring
- [ ] Implement backup strategy
- [ ] Document API usage
- [ ] Create user guide

## Technical Stack
- **Language**: Python 3.9+
- **MCP Framework**: FastMCP
- **Embeddings**: VoyageAI (voyage-law-2)
- **Vector DB**: ChromaDB
- **XML Parsing**: lxml
- **HTTP Client**: httpx
- **Testing**: pytest

## Key Decisions
1. **Chunking Strategy**: Section-level chunking with hierarchical context
2. **Embedding Model**: voyage-law-2 (optimized for legal text)
3. **Vector Database**: ChromaDB (simple, embedded, good for POC)
4. **Search Strategy**: Semantic search with reranking

## Success Criteria
1. Successfully download and process USC XML files
2. Generate high-quality embeddings for all content
3. Provide <100ms search response times
4. Return relevant results with proper citations
5. Support concurrent AI agent queries

## Risk Mitigation
1. **API Rate Limits**: Implement exponential backoff
2. **Large Data Volume**: Process in batches, use streaming
3. **Memory Constraints**: Implement chunked processing
4. **Search Quality**: Use reranking, collect feedback

## Questions for User
1. Which USC title should we use for the initial sample? (Recommend Title 26 - Tax Code)
2. Do you have preferences for the vector database? (ChromaDB vs Pinecone vs Weaviate)
3. What's the expected query volume from AI agents?
4. Do you need any specific search features beyond semantic search?
5. Should we include historical versions or just current USC?