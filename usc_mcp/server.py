"""
FastMCP Server for USC Semantic Search

Provides MCP interface for AI agents to search and access US Code.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

from fastmcp import FastMCP
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from usc_mcp.database import ChromaDatabase
from usc_mcp.embedder import VoyageEmbedder
from usc_mcp.tools import USCSearchTools, SearchResult, CitationResult, BrowseResult

# Load environment variables
load_dotenv()

# Configure logging
log_file = os.path.expanduser("~/usc_mcp_debug.log")
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also log to stderr
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"USC MCP Server logging to: {log_file}")

# Initialize MCP server
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "USC Semantic Search")
)

# Initialize components
logger.info("Initializing USC MCP components...")

database = None
embedder = None
tools = None

try:
    logger.info("Initializing ChromaDB...")
    database = ChromaDatabase()
    stats = database.get_stats()
    logger.info(f"Database initialized with {stats['total_sections']} sections")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}", exc_info=True)
    database = None

try:
    logger.info("Initializing VoyageEmbedder...")
    embedder = VoyageEmbedder()
    logger.info("Embedder initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize embedder: {e}", exc_info=True)
    embedder = None

if database and embedder:
    try:
        logger.info("Initializing USCSearchTools...")
        tools = USCSearchTools(database, embedder)
        logger.info("Tools initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools: {e}", exc_info=True)
        tools = None
else:
    logger.error("Cannot initialize tools - database or embedder failed")
    tools = None

logger.info(f"Initialization complete. Database: {database is not None}, Embedder: {embedder is not None}, Tools: {tools is not None}")

@mcp.tool
async def search_usc(
    query: str,
    limit: int = 10,
    title: Optional[str] = None,  # Accept string to handle Claude's input
    rerank: bool = True
) -> List[dict]:
    """
    Search United States Code using natural language queries.
    
    This tool performs semantic search across USC sections to find relevant
    legal provisions based on your query. It uses AI embeddings optimized
    for legal text.
    
    Args:
        query: Natural language search query (e.g., "home office tax deduction")
        limit: Maximum number of results to return (default: 10)
        title: Optional USC title number to search within (e.g., 26 for Tax Code)
        rerank: Whether to use AI reranking for better relevance (default: True)
        
    Returns:
        List of search results with citations, text snippets, and relevance scores
        
    Examples:
        - search_usc("capital gains tax on real estate")
        - search_usc("medical expense deductions", title=26, limit=5)
        - search_usc("employment discrimination", title=42)
    """
    global database, embedder, tools
    
    # Check if we need to initialize (lazy initialization)
    if tools is None:
        logger.info("Tools not initialized, performing lazy initialization...")
        try:
            database = ChromaDatabase()
            embedder = VoyageEmbedder()
            tools = USCSearchTools(database, embedder)
            logger.info("Lazy initialization successful")
        except Exception as e:
            logger.error(f"Lazy initialization failed: {e}", exc_info=True)
            return [{
                "error": "Initialization failed",
                "message": f"Failed to initialize USC tools: {str(e)}"
            }]
    
    if not tools:
        logger.error("Tools still not initialized after lazy init")
        return [{
            "error": "Server not properly initialized",
            "message": "The USC search tools are not available. Check server logs."
        }]
    
    try:
        # Convert title to int if provided
        title_int = int(title) if title is not None else None
        logger.info(f"Searching USC for: '{query}', title={title_int}, limit={limit}")
        results = await tools.search_usc(query, limit, title_int, rerank)
        logger.info(f"Search returned {len(results)} results")
        return [result.to_dict() for result in results]
    except Exception as e:
        logger.error(f"Error in search_usc: {e}", exc_info=True)
        return [{
            "error": str(e),
            "message": "Failed to search USC. Please try again."
        }]

@mcp.tool
async def get_citation(citation: str) -> Optional[dict]:
    """
    Retrieve a specific USC section by its legal citation.
    
    This tool fetches the complete text of a USC section when you know
    the exact citation. It returns the full text and metadata.
    
    Args:
        citation: Legal citation in standard format
                 Examples: "26 USC 280A", "42 USC 2000e", "26 § 162"
                 
    Returns:
        Complete section text with metadata, or None if not found
        
    Examples:
        - get_citation("26 USC 280A")  # Home office deduction
        - get_citation("26 § 162")     # Business expenses
        - get_citation("42 USC 12101") # ADA definitions
    """
    global database, embedder, tools
    
    # Check if we need to initialize (lazy initialization)
    if tools is None:
        logger.info("Tools not initialized, performing lazy initialization...")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Script location: {os.path.abspath(__file__)}")
        try:
            database = ChromaDatabase()
            logger.info(f"Database initialized at: {database.persist_dir}")
            stats = database.get_stats()
            logger.info(f"Database has {stats['total_sections']} sections")
            
            embedder = VoyageEmbedder()
            tools = USCSearchTools(database, embedder)
            logger.info("Lazy initialization successful")
        except Exception as e:
            logger.error(f"Lazy initialization failed: {e}", exc_info=True)
            return {
                "error": "Initialization failed",
                "message": f"Failed to initialize USC tools: {str(e)}"
            }
    
    if not tools:
        logger.error("Tools still not initialized after lazy init")
        return {
            "error": "Server not properly initialized",
            "message": "The USC search tools are not available. Check server logs."
        }
        
    try:
        logger.info(f"Looking up citation: '{citation}'")
        result = await tools.get_citation(citation)
        if result:
            logger.info(f"Found citation: {result.citation}")
            return result.to_dict()
        else:
            logger.info(f"Citation not found: {citation}")
            return None
    except Exception as e:
        logger.error(f"Error in get_citation: {e}", exc_info=True)
        return {
            "error": str(e),
            "message": f"Failed to retrieve citation: {citation}"
        }

@mcp.tool
async def browse_usc(
    title: Optional[str] = None,  # Accept string to handle Claude's input
    chapter: Optional[str] = None  # Accept string to handle Claude's input
) -> dict:
    """
    Browse the USC hierarchy to explore titles, chapters, and sections.
    
    This tool allows navigation through the USC structure:
    - Without arguments: lists all USC titles
    - With title only: lists chapters in that title
    - With title and chapter: lists sections in that chapter
    
    Args:
        title: Optional USC title number (1-54)
        chapter: Optional chapter number (requires title)
        
    Returns:
        Hierarchical listing of USC components
        
    Examples:
        - browse_usc()           # List all titles
        - browse_usc(title=26)   # List chapters in Title 26 (Tax Code)
        - browse_usc(title=26, chapter=1)  # List sections in Chapter 1
    """
    try:
        # Convert to int if provided
        title_int = int(title) if title is not None else None
        chapter_int = int(chapter) if chapter is not None else None
        result = await tools.browse_usc(title_int, chapter_int)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Error in browse_usc: {e}")
        return {
            "error": str(e),
            "level": "error",
            "items": []
        }

@mcp.tool
async def get_context(
    section_id: str,
    context_size: int = 2
) -> List[dict]:
    """
    Get surrounding sections for better context understanding.
    
    This tool retrieves a USC section along with nearby sections to provide
    fuller context. Useful for understanding how provisions relate to each other.
    
    Args:
        section_id: Section identifier (format: "title-section", e.g., "26-280A")
        context_size: Number of sections before and after to include (default: 2)
        
    Returns:
        List of sections including the target and surrounding context
        
    Examples:
        - get_context("26-280A", context_size=2)    # Home office with context
        - get_context("42-2000e", context_size=3)   # Title VII with context
    """
    try:
        results = await tools.get_context(section_id, context_size)
        return [result.to_dict() for result in results]
    except Exception as e:
        logger.error(f"Error in get_context: {e}")
        return [{
            "error": str(e),
            "message": f"Failed to get context for section: {section_id}"
        }]

@mcp.tool
async def test_connection() -> dict:
    """
    Test if the USC MCP server is working properly.
    
    Returns:
        Status of server components
    """
    logger.info("Test connection called")
    return {
        "status": "connected",
        "database": "initialized" if database else "failed",
        "embedder": "initialized" if embedder else "failed",
        "tools": "initialized" if tools else "failed",
        "message": "USC MCP Server is running"
    }

@mcp.tool
async def get_database_stats() -> dict:
    """
    Get statistics about the USC database.
    
    Returns information about the current state of the semantic search database,
    including number of sections indexed, titles covered, and last update time.
    
    Returns:
        Database statistics and metadata
    """
    try:
        stats = database.get_stats()
        
        # Determine active embedding model
        if embedder.use_contextualized:
            active_model = embedder.context_model
            embedding_type = "contextualized"
        else:
            active_model = embedder.embedding_model
            embedding_type = "standard"
            
        return {
            "status": "online",
            "statistics": stats,
            "embedding_configuration": {
                "active_model": active_model,
                "embedding_type": embedding_type,
                "standard_model": embedder.embedding_model,
                "context_model": embedder.context_model,
                "context_dimension": embedder.context_dimension if embedder.use_contextualized else None,
                "use_contextualized": embedder.use_contextualized
            },
            "features": {
                "semantic_search": True,
                "contextualized_embeddings": embedder.use_contextualized,
                "reranking": True,
                "hierarchical_browse": True,
                "citation_lookup": True
            }
        }
    except Exception as e:
        logger.error(f"Error in get_database_stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Health check endpoint
@mcp.tool
async def health_check() -> dict:
    """
    Check if the USC search service is operational.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "USC Semantic Search",
        "version": "0.1.0",
        "components": {
            "database": "operational",
            "embedder": "operational",
            "tools": "operational"
        }
    }

def main():
    """Run the MCP server"""
    logger.info("Starting USC Semantic Search MCP Server")
    
    # Check if components are initialized
    if database:
        logger.info(f"Database: {database.persist_dir}")
        try:
            stats = database.get_stats()
            logger.info(f"Database contains {stats['total_sections']} sections from {stats['unique_titles']} titles")
        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
    else:
        logger.error("Database not initialized!")
        
    if embedder:
        logger.info(f"Embedding model: {embedder.embedding_model}")
    else:
        logger.error("Embedder not initialized!")
        
    if database:
        logger.info(f"Collection: {database.collection_name}")
        
    if not tools:
        logger.error("Tools not initialized! Server will not function properly.")
    else:
        logger.info("All components initialized successfully")
    
    # Run the server
    logger.info("Starting MCP server on STDIO...")
    mcp.run()

if __name__ == "__main__":
    main()