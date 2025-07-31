#!/usr/bin/env python3

from usc_mcp.database import ChromaDatabase

db = ChromaDatabase()
result = db.get_by_id('26-§ 199A.')

if result:
    print('=== METADATA ===')
    for key, value in result['metadata'].items():
        if key != 'text':  # Skip text field 
            if isinstance(value, str) and len(value) > 100:
                print(f'{key}: {value[:100]}...')
            else:
                print(f'{key}: {value}')
    
    print('\n=== DOCUMENT ===')
    doc = result.get('document', '')
    print(f'Document length: {len(doc)} characters')
    print(f'First 500 chars: {doc[:500]}')
    
    # Check if text is in metadata
    text = result['metadata'].get('text', '')
    print(f'\n=== TEXT FIELD ===')
    print(f'Text length: {len(text)} characters')
    if text:
        print(f'First 500 chars: {text[:500]}')
    else:
        print('Text field is empty!')
        
    # Check for chunks
    import json
    if 'chunks' in result['metadata']:
        chunks = result['metadata']['chunks']
        if chunks.startswith('['):
            try:
                chunks_list = json.loads(chunks)
                print(f'\n=== CHUNKS ===')
                print(f'Number of chunks: {len(chunks_list)}')
                total_text = ' '.join(chunks_list)
                print(f'Total text from chunks: {len(total_text)} characters')
                if total_text:
                    print(f'First 500 chars of chunk text: {total_text[:500]}')
            except Exception as e:
                print(f'Could not parse chunks: {e}')
else:
    print('Section 199A not found')