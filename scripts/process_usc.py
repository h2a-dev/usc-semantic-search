#!/usr/bin/env python3
"""
Process and embed USC XML files

Parses downloaded USC XML files and generates embeddings for semantic search.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from usc_mcp.parser import USLMParser
from usc_mcp.embedder import VoyageEmbedder
from usc_mcp.database import ChromaDatabase

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

class USCProcessor:
    """Process USC XML files and generate embeddings"""
    
    def __init__(self, data_dir: str = "./data/xml"):
        self.data_dir = Path(data_dir)
        self.parser = USLMParser()
        self.embedder = VoyageEmbedder()
        self.database = ChromaDatabase()
        
    def get_xml_files(self, title_nums: List[int] = None) -> List[Path]:
        """Get list of XML files to process"""
        xml_files = []
        
        if title_nums:
            # Specific titles requested
            for title_num in title_nums:
                filepath = self.data_dir / f"usc{str(title_num).zfill(2)}.xml"
                if filepath.exists():
                    xml_files.append(filepath)
                else:
                    console.print(f"[yellow]Warning: Title {title_num} XML not found[/yellow]")
        else:
            # Process all XML files
            xml_files = list(self.data_dir.glob("usc*.xml"))
            
        return sorted(xml_files)
        
    async def process_file(self, filepath: Path) -> int:
        """Process a single USC XML file"""
        console.print(f"\n[cyan]Processing {filepath.name}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Parse XML
            task = progress.add_task("Parsing XML...", total=None)
            sections = self.parser.parse_file(filepath)
            progress.update(task, completed=True)
            
            if not sections:
                console.print(f"[yellow]No sections found in {filepath.name}[/yellow]")
                return 0
                
            console.print(f"[green]Parsed {len(sections)} sections[/green]")
            
            # Extract chunks
            task = progress.add_task("Extracting chunks...", total=None)
            chunks = self.parser.extract_chunks(
                sections,
                max_tokens=int(os.getenv("MAX_TOKENS_PER_CHUNK", 1000)),
                overlap=int(os.getenv("CHUNK_OVERLAP", 100))
            )
            
            # Filter out empty chunks
            non_empty_chunks = []
            for chunk in chunks:
                if chunk.get('text') and chunk['text'].strip():
                    non_empty_chunks.append(chunk)
                else:
                    console.print(f"[yellow]Skipping empty chunk: {chunk.get('id', 'unknown')}[/yellow]")
            
            chunks = non_empty_chunks
            progress.update(task, completed=True)
            
            console.print(f"[green]Created {len(chunks)} chunks[/green]")
            
            if not chunks:
                console.print(f"[yellow]No valid chunks to process for {filepath.name}[/yellow]")
                return 0
            
            # Estimate cost
            avg_chunk_size = sum(len(chunk['text'].split()) for chunk in chunks) // len(chunks) if chunks else 0
            cost_estimate = self.embedder.estimate_cost(len(chunks), avg_chunk_size)
            console.print(f"[yellow]Estimated embedding cost: ${cost_estimate['embedding_cost']:.4f}[/yellow]")
            
            # Generate embeddings
            task = progress.add_task("Generating embeddings...", total=None)
            
            # Use async embedding for better performance
            embedding_results = await self.embedder.embed_chunks_async(chunks)
            
            progress.update(task, completed=True)
            
            console.print(f"[green]Generated {len(embedding_results)} embeddings[/green]")
            
            # Store in database
            task = progress.add_task("Storing in database...", total=None)
            stored = self.database.add_embeddings(embedding_results)
            progress.update(task, completed=True)
            
            console.print(f"[green]Stored {stored} embeddings in database[/green]")
            
            return stored
            
    async def process_all(self, title_nums: List[int] = None):
        """Process multiple USC files"""
        xml_files = self.get_xml_files(title_nums)
        
        if not xml_files:
            console.print("[red]No XML files found to process[/red]")
            return
            
        console.print(f"\n[bold]Found {len(xml_files)} XML files to process[/bold]")
        
        total_sections = 0
        
        for filepath in xml_files:
            try:
                sections_processed = await self.process_file(filepath)
                total_sections += sections_processed
            except Exception as e:
                console.print(f"[red]Error processing {filepath.name}: {e}[/red]")
                logger.error(f"Error processing {filepath}: {e}", exc_info=True)
                
        # Print summary
        console.print(f"\n[bold green]Processing complete![/bold green]")
        console.print(f"Total sections processed: {total_sections}")
        
        # Show database stats
        stats = self.database.get_stats()
        console.print(f"\n[bold]Database Statistics:[/bold]")
        console.print(f"Total sections: {stats['total_sections']}")
        console.print(f"Unique titles: {stats['unique_titles']}")
        console.print(f"Unique chapters: {stats['unique_chapters']}")

@click.command()
@click.option("--title", "-t", multiple=True, type=int, help="Specific title number(s) to process")
@click.option("--all", "process_all", is_flag=True, help="Process all downloaded USC titles")
@click.option("--clear", is_flag=True, help="Clear existing database before processing")
@click.option("--data-dir", default="./data/xml", help="Directory containing USC XML files")
def main(title, process_all, clear, data_dir):
    """Process USC XML files and generate embeddings"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    processor = USCProcessor(data_dir)
    
    # Clear database if requested
    if clear:
        console.print("[yellow]Clearing existing database...[/yellow]")
        processor.database.clear_collection()
        
    # Determine which titles to process
    if process_all:
        title_nums = None
        console.print("[bold]Processing all USC titles...[/bold]")
    elif title:
        title_nums = list(title)
        console.print(f"[bold]Processing USC title(s): {', '.join(map(str, title_nums))}[/bold]")
    else:
        # Default to Title 26 if nothing specified
        title_nums = [26]
        console.print("[bold]No titles specified, processing Title 26 (Tax Code)[/bold]")
        
    # Run processing
    asyncio.run(processor.process_all(title_nums))

if __name__ == "__main__":
    main()