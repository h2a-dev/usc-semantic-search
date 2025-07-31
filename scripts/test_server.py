#!/usr/bin/env python3
"""
Test the USC MCP server functionality
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from usc_mcp.database import ChromaDatabase
from usc_mcp.embedder import VoyageEmbedder
from usc_mcp.tools import USCSearchTools


async def test_server():
    """Test basic server functionality"""
    print("Testing USC MCP Server Components...")

    # Initialize components
    print("\n1. Initializing components...")
    try:
        database = ChromaDatabase()
        print("✓ Database initialized")

        embedder = VoyageEmbedder()
        print("✓ Embedder initialized")

        tools = USCSearchTools(database, embedder)
        print("✓ Tools initialized")
    except Exception as e:
        print(f"✗ Error initializing components: {e}")
        return

    # Check database stats
    print("\n2. Checking database...")
    try:
        stats = database.get_stats()
        print(f"✓ Database contains {stats['total_sections']} sections")
        print(
            f"  Titles: {', '.join(stats['titles'][:5])}{'...' if len(stats['titles']) > 5 else ''}"
        )
    except Exception as e:
        print(f"✗ Error checking database: {e}")

    # Test search (if database has content)
    if stats["total_sections"] > 0:
        print("\n3. Testing search...")
        try:
            results = await tools.search_usc("tax deduction", limit=3, rerank=False)
            print(f"✓ Search returned {len(results)} results")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result.citation}: {result.section_name}")
        except Exception as e:
            print(f"✗ Error testing search: {e}")

        # Test citation lookup
        print("\n4. Testing citation lookup...")
        try:
            if results:
                citation = results[0].citation
                result = await tools.get_citation(citation)
                if result:
                    print(f"✓ Retrieved citation: {result.citation}")
                    print(f"  Title: {result.title}")
                    print(f"  Section: {result.section_name}")
                else:
                    print(f"✗ Could not retrieve citation: {citation}")
        except Exception as e:
            print(f"✗ Error testing citation lookup: {e}")
    else:
        print("\n⚠ Database is empty. Run process_usc.py first to add content.")

    print("\n✓ Test complete!")


def main():
    """Main entry point for testing"""
    asyncio.run(test_server())


if __name__ == "__main__":
    main()
