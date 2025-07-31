# Voyage Context-3 Implementation Plan for USC Semantic Search

## Overview

This document outlines the implementation plan for upgrading the USC Semantic Search MCP Server from standard embeddings (`voyage-law-2`) to contextualized chunk embeddings (`voyage-context-3`).

## Current State Analysis

### Current Implementation
- **Model**: `voyage-law-2` (standard embeddings)
- **Chunking**: Each USC section is treated as a single chunk
- **Context**: No cross-section context is preserved
- **Embedding**: Standard `embed()` method is used

### Limitations
1. Loss of context when sections reference other sections
2. No hierarchical context (chapter → section relationships)
3. Subsections lose parent section context
4. Cross-references between sections are not captured

## Implementation Strategy

### 1. Enhanced Chunking Strategy

Instead of treating each section as a single chunk, we'll implement a multi-level chunking approach:

```python
# Document levels for USC:
# Title → Chapter → Section → Subsection → Paragraph

# Chunking strategy:
# - Level 1: Chapter as document, sections as chunks
# - Level 2: Section as document, subsections as chunks
# - Level 3: Large sections split into semantic chunks
```

### 2. Context Preservation

Each chunk will maintain its hierarchical context:
- Chapter context for sections
- Section context for subsections
- Cross-reference context when sections cite others

### 3. Model Configuration

```python
# New configuration
VOYAGE_CONTEXT_MODEL = "voyage-context-3"
VOYAGE_CONTEXT_DIMENSION = 1024  # Default, can be 256, 512, 1024, 2048
VOYAGE_MAX_CONTEXT_LENGTH = 32000  # tokens
```

## Implementation Steps

### Phase 1: Update Embedder Module

**File**: `usc_mcp/embedder.py`

1. Add support for contextualized embeddings:
   ```python
   def contextualized_embed_chunks(self, 
                                   document_chunks: List[List[Dict[str, Any]]], 
                                   show_progress: bool = True) -> List[EmbeddingResult]:
       """
       Embed chunks with document context
       
       Args:
           document_chunks: List of documents, each containing list of chunks
       """
   ```

2. Add configuration for context model:
   ```python
   context_embedding_model: str = "voyage-context-3"
   use_contextualized: bool = True
   ```

3. Update query embedding to use context model:
   ```python
   def embed_query_contextual(self, query: str) -> List[float]:
       """Embed query using contextualized model"""
   ```

### Phase 2: Enhanced Parser Module

**File**: `usc_mcp/parser.py`

1. Implement hierarchical chunking:
   ```python
   def extract_contextual_chunks(self, 
                                sections: List[USCSection], 
                                chunk_strategy: str = "hierarchical") -> List[List[Dict[str, Any]]]:
       """
       Extract chunks maintaining document boundaries
       
       Returns:
           List of documents, each containing ordered chunks
       """
   ```

2. Add chunking strategies:
   - **Hierarchical**: Chapter → Sections → Subsections
   - **Section-based**: Each section with its subsections
   - **Smart splitting**: Split large sections while preserving boundaries

3. Maintain document metadata:
   ```python
   {
       "document_id": "26-chapter-1",  # Chapter level
       "chunks": [
           {
               "id": "26-1-162",
               "text": "Section text...",
               "position": 0,
               "metadata": {...}
           }
       ]
   }
   ```

### Phase 3: Database Updates

**File**: `usc_mcp/database.py`

1. Add document-chunk relationship tracking:
   ```python
   def add_contextualized_embeddings(self, 
                                    embedding_results: List[ContextualizedEmbeddingResult]) -> int:
       """Store embeddings with document context metadata"""
   ```

2. Update search to handle contextualized queries:
   ```python
   def search_contextual(self, 
                        query_embedding: List[float], 
                        limit: int = 10,
                        filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
       """Search using contextualized embeddings"""
   ```

### Phase 4: Processing Script Updates

**File**: `scripts/process_usc.py`

1. Add flag for contextualized processing:
   ```bash
   python process_usc.py --title 26 --use-context
   ```

2. Implement batch processing for document groups:
   ```python
   def process_with_context(self, xml_files: List[Path]):
       """Process files maintaining document boundaries"""
   ```

### Phase 5: Server Integration

**File**: `usc_mcp/server.py`

1. Add configuration option:
   ```python
   USE_CONTEXTUALIZED_EMBEDDINGS = os.getenv("USE_CONTEXTUALIZED_EMBEDDINGS", "true")
   ```

2. Update search tools to use appropriate embedder

## Configuration Updates

### Environment Variables

```env
# Existing
VOYAGE_API_KEY=your_key
VOYAGE_EMBEDDING_MODEL=voyage-law-2

# New additions
VOYAGE_CONTEXT_MODEL=voyage-context-3
VOYAGE_CONTEXT_DIMENSION=1024
USE_CONTEXTUALIZED_EMBEDDINGS=true
CHUNK_STRATEGY=hierarchical
```

### Performance Considerations

1. **Batch Processing**: Process chunks in document groups
2. **Token Limits**: 
   - Max 120K tokens per batch
   - Max 16K chunks per batch
   - Max 1000 documents per batch
3. **Memory**: Increased memory usage due to document grouping

## Migration Strategy

1. **Backward Compatibility**: Keep both embedding methods available
2. **Gradual Migration**: 
   - Start with new titles using context embeddings
   - Migrate existing titles gradually
3. **A/B Testing**: Compare search quality between methods

## Testing Plan

1. **Unit Tests**:
   - Test contextualized embedding generation
   - Test document boundary preservation
   - Test search with both methods

2. **Integration Tests**:
   - End-to-end processing with sample USC data
   - Search quality comparison
   - Performance benchmarks

3. **Quality Metrics**:
   - Search relevance scores
   - Context preservation validation
   - Cross-reference accuracy

## Benefits Expected

1. **Better Context Understanding**:
   - Subsections maintain section context
   - Related provisions are better connected
   - Cross-references are semantically linked

2. **Improved Search Quality**:
   - More accurate results for complex queries
   - Better handling of ambiguous terms
   - Improved relevance for multi-part questions

3. **Legal-Specific Advantages**:
   - Better understanding of statutory structure
   - Improved citation context
   - More accurate cross-reference resolution

## Implementation Timeline

- **Week 1**: Update embedder and parser modules
- **Week 2**: Database and processing script updates
- **Week 3**: Server integration and testing
- **Week 4**: Documentation and deployment

## Rollback Plan

If issues arise:
1. Environment variable to disable contextualized embeddings
2. Fallback to standard embeddings
3. Separate collections for each embedding type
4. Gradual rollback per title if needed