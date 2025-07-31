#!/usr/bin/env python3
"""Debug script to check what's in the USC database"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from usc_mcp.database import ChromaDatabase

def main():
    # Initialize database
    db = ChromaDatabase()
    
    print(f"Database path: {db.persist_dir}")
    print(f"Collection name: {db.collection_name}")
    
    # Get stats
    stats = db.get_stats()
    print(f"\nDatabase stats:")
    print(f"  Total sections: {stats['total_sections']}")
    print(f"  Unique titles: {stats['unique_titles']}")
    print(f"  Titles: {', '.join(stats['titles'][:10])}...")
    
    # Get a sample section
    print("\nTrying to get section 26 USC 1...")
    result = db.get_by_citation("26 USC 1")
    if not result:
        print("  Not found by citation, trying by ID...")
        # Try different ID formats
        for section_id in ["26-§ 1.", "26-§ 1", "26-1.", "26-1"]:
            result = db.get_by_id(section_id)
            if result:
                print(f"  Found with ID: {section_id}")
                break
    
    if result:
        print(f"\nSection found:")
        print(f"  ID: {result['id']}")
        print(f"  Document: {result['document'][:100]}...")
        print(f"\nMetadata keys: {list(result['metadata'].keys())}")
        
        # Check if 'text' field exists
        if 'text' in result['metadata']:
            text = result['metadata']['text']
            print(f"  Text field length: {len(text)} characters")
            if text:
                print(f"  Text preview: {text[:200]}...")
            else:
                print("  Text field is empty!")
        else:
            print("  WARNING: 'text' field is missing from metadata!")
            
        # Show all metadata
        print("\nAll metadata fields:")
        for key, value in result['metadata'].items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    else:
        print("Section not found!")
        
    # Try to get any random section to see structure
    print("\n\nGetting a random section to check structure...")
    sample = db.collection.get(limit=1, include=['metadatas', 'documents'])
    if sample['ids']:
        print(f"Sample section ID: {sample['ids'][0]}")
        print(f"Sample document: {sample['documents'][0][:100]}...")
        print(f"Sample metadata keys: {list(sample['metadatas'][0].keys())}")

if __name__ == "__main__":
    main()