#!/usr/bin/env python3

from usc_mcp.database import ChromaDatabase

db = ChromaDatabase()

# Check multiple sections
sections_to_check = [
    '26-§ 1.',
    '26-§ 63.',
    '26-§ 151.',
    '26-§ 24.',
    '26-§ 199A.',
    '26-§ 162.',
    '26-§ 280A.'
]

print("Checking multiple sections for text content:\n")

for section_id in sections_to_check:
    result = db.get_by_id(section_id)
    if result:
        text = result['metadata'].get('text', '')
        doc = result.get('document', '')
        citation = result['metadata'].get('full_citation', section_id)
        
        print(f"Section: {citation}")
        print(f"  - Text field length: {len(text)} chars")
        print(f"  - Document field length: {len(doc)} chars")
        if text:
            print(f"  - Text preview: {text[:100]}...")
        else:
            print(f"  - WARNING: Text field is empty!")
        print()
    else:
        print(f"Section {section_id} not found\n")

# Check database stats
stats = db.get_stats()
print(f"\nDatabase stats:")
print(f"Total sections: {stats['total_sections']}")
print(f"Database path: {stats['database_path']}")