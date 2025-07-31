#!/usr/bin/env python3
"""
Download United States Code XML files from uscode.house.gov
"""

import os
import sys
import time
import asyncio
import logging
import zipfile
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

import httpx
import click
from rich.console import Console
from rich.progress import Progress, DownloadColumn, BarColumn, TextColumn, TimeRemainingColumn
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


class USCDownloader:
    """Downloads USC XML files with rate limiting and retry logic"""

    def __init__(self, data_dir: str, base_url: str = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url or "https://uscode.house.gov"
        self.download_page_url = f"{self.base_url}/download/download.shtml"
        self.catalog_file = self.data_dir / "download_catalog.json"
        self.session = None

    async def __aenter__(self):
        # Use browser-like headers to avoid getting blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = httpx.AsyncClient(timeout=60.0, follow_redirects=True, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def fetch_download_catalog(self) -> Dict[str, Dict[str, str]]:
        """Fetch and parse the download page to get all USC title links"""
        console.print("[cyan]Fetching USC download catalog...[/cyan]")

        try:
            response = await self.session.get(self.download_page_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the table with USC titles
            catalog = {}

            # Look for all links that contain XML downloads
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)

                # Match patterns like "xml_usc07@119-23not21.zip"
                if "xml_usc" in href and href.endswith(".zip"):
                    # Extract title number from filename
                    import re

                    match = re.search(r"xml_usc(\d+)@", href)
                    if match:
                        title_num = int(match.group(1))

                        # Get full URL - handle relative paths properly
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("/"):
                            full_url = self.base_url + href
                        else:
                            # For relative paths like "releasepoints/..."
                            # The links are relative to /download/ page
                            full_url = self.base_url + "/download/" + href

                        # Extract version/release point
                        version_match = re.search(r"@(.+?)\.zip", href)
                        version = version_match.group(1) if version_match else "unknown"

                        catalog[str(title_num)] = {
                            "url": full_url,
                            "filename": os.path.basename(href),
                            "version": version,
                            "text": text,
                            "updated": datetime.now().isoformat(),
                        }

            # Save catalog to file
            with open(self.catalog_file, "w") as f:
                json.dump(catalog, f, indent=2)

            console.print(f"[green]✓ Found {len(catalog)} USC titles in catalog[/green]")
            return catalog

        except Exception as e:
            console.print(f"[red]Error fetching catalog: {e}[/red]")

            # Try to load cached catalog
            if self.catalog_file.exists():
                console.print("[yellow]Loading cached catalog...[/yellow]")
                with open(self.catalog_file, "r") as f:
                    return json.load(f)
            else:
                raise

    def load_catalog(self) -> Dict[str, Dict[str, str]]:
        """Load catalog from file if it exists"""
        if self.catalog_file.exists():
            with open(self.catalog_file, "r") as f:
                return json.load(f)
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def download_file(self, url: str, filepath: Path, progress=None, task_id=None):
        """Download a file with retry logic"""
        # Try with a simpler approach - just get the content
        response = await self.session.get(url)
        response.raise_for_status()

        # Check if we got HTML instead of a zip file
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            console.print("[red]Warning: Got HTML response instead of zip file[/red]")
            console.print("[dim]Content-Type: " + content_type + "[/dim]")
            console.print(f"[dim]Status: {response.status_code}[/dim]")
            # Check first 200 chars
            text_preview = response.text[:200]
            if "document not found" in text_preview.lower():
                raise Exception("Document not found - URL may be incorrect")

        # Write the content
        content = response.content
        total = len(content)

        if progress and task_id is not None:
            progress.update(task_id, total=total)

        with open(filepath, "wb") as f:
            f.write(content)
            if progress and task_id is not None:
                progress.update(task_id, advance=total)

        return filepath

    async def download_and_extract_title(
        self, title_num: int, title_info: Dict[str, str], progress=None, force: bool = False
    ) -> Optional[Path]:
        """Download and extract a USC title zip file"""
        zip_filename = title_info["filename"]
        zip_filepath = self.data_dir / zip_filename
        xml_filename = f"usc{str(title_num).zfill(2)}.xml"
        xml_filepath = self.data_dir / xml_filename

        # Check if already extracted
        if xml_filepath.exists() and not force:
            console.print(f"[yellow]Title {title_num} already extracted, skipping[/yellow]")
            return xml_filepath

        # Download zip file if needed
        if not zip_filepath.exists() or force:
            task_id = None
            if progress:
                task_id = progress.add_task(
                    f"Title {title_num}", start=True, filename=zip_filename, total=100
                )

            try:
                console.print(f"[cyan]Downloading {zip_filename}...[/cyan]")
                console.print(f"[dim]URL: {title_info['url']}[/dim]")
                await self.download_file(title_info["url"], zip_filepath, progress, task_id)
                console.print(f"[green]✓ Downloaded {zip_filename}[/green]")
            except httpx.HTTPError as e:
                console.print(f"[red]✗ Failed to download Title {title_num}: {e}[/red]")
                if progress and task_id is not None:
                    progress.remove_task(task_id)
                return None

        # Extract zip file
        try:
            console.print(f"[cyan]Extracting {zip_filename}...[/cyan]")
            with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
                # Find the XML file in the zip
                xml_files = [f for f in zip_ref.namelist() if f.endswith(".xml")]
                if xml_files:
                    # Extract the first XML file
                    zip_ref.extract(xml_files[0], self.data_dir)
                    extracted_path = self.data_dir / xml_files[0]

                    # Rename to standard format
                    if extracted_path != xml_filepath:
                        extracted_path.rename(xml_filepath)

                    console.print(f"[green]✓ Extracted Title {title_num}[/green]")

                    # Optionally remove zip file to save space
                    # zip_filepath.unlink()

                    return xml_filepath
                else:
                    console.print(f"[red]No XML file found in {zip_filename}[/red]")
                    return None

        except Exception as e:
            console.print(f"[red]Error extracting {zip_filename}: {e}[/red]")
            return None

    async def download_schema_files(self) -> bool:
        """Download XML schema files"""
        schema_dir = self.data_dir / "schema"
        schema_dir.mkdir(exist_ok=True)

        schema_files = ["USLM-1.0.xsd", "dc.xsd", "dcmitype.xsd", "dcterms.xsd"]

        console.print("[cyan]Downloading schema files...[/cyan]")

        for schema_file in schema_files:
            url = f"{self.base_url}/download/{schema_file}"
            filepath = schema_dir / schema_file

            if filepath.exists():
                continue

            try:
                await self.download_file(url, filepath)
                console.print(f"[green]✓ Downloaded {schema_file}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed to download {schema_file}: {e}[/red]")
                return False

        return True

    async def download_titles(
        self, titles: List[int], update_catalog: bool = True, force: bool = False
    ) -> List[Path]:
        """Download multiple USC titles"""
        downloaded = []

        # Update catalog if requested or if it doesn't exist
        if update_catalog or not self.catalog_file.exists():
            catalog = await self.fetch_download_catalog()
        else:
            catalog = self.load_catalog()

        if not catalog:
            console.print("[red]No catalog available. Cannot download titles.[/red]")
            return []

        # Filter titles that exist in catalog
        available_titles = []
        for title in titles:
            if str(title) in catalog:
                available_titles.append(title)
            else:
                console.print(f"[yellow]Warning: Title {title} not found in catalog[/yellow]")

        if not available_titles:
            console.print("[red]No valid titles to download[/red]")
            return []

        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # Add rate limiting to avoid overwhelming the server
            for i, title in enumerate(available_titles):
                if i > 0:
                    await asyncio.sleep(1)  # 1 second between downloads

                title_info = catalog[str(title)]
                result = await self.download_and_extract_title(title, title_info, progress, force)
                if result:
                    downloaded.append(result)

        return downloaded


@click.command()
@click.option("--title", "-t", multiple=True, type=int, help="Specific title number(s) to download")
@click.option("--all", "download_all", is_flag=True, help="Download all USC titles")
@click.option("--sample", is_flag=True, help="Download sample titles (1, 26, 42)")
@click.option("--update-catalog", is_flag=True, help="Update the download catalog from the website")
@click.option("--list-available", is_flag=True, help="List all available titles")
@click.option("--force", is_flag=True, help="Force re-download even if files exist")
@click.option("--data-dir", default="./data/xml", help="Directory to store downloaded files")
def main(title, download_all, sample, update_catalog, list_available, force, data_dir):
    """Download United States Code XML files"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def run():
        async with USCDownloader(data_dir) as downloader:
            # Update catalog if requested
            if update_catalog:
                await downloader.fetch_download_catalog()

            # List available titles if requested
            if list_available:
                catalog = downloader.load_catalog()
                if not catalog:
                    catalog = await downloader.fetch_download_catalog()

                console.print("\n[bold]Available USC Titles:[/bold]")
                for title_num in sorted(catalog.keys(), key=int):
                    info = catalog[title_num]
                    console.print(
                        f"  Title {title_num}: {info['filename']} (version: {info['version']})"
                    )
                return

            # Determine which titles to download
            if download_all:
                catalog = downloader.load_catalog()
                if not catalog:
                    catalog = await downloader.fetch_download_catalog()
                titles = [int(t) for t in catalog.keys()]
                console.print(f"[bold]Downloading all {len(titles)} USC titles...[/bold]")
            elif sample:
                titles = [1, 26, 42]  # Small, Tax, Public Health
                console.print("[bold]Downloading sample USC titles (1, 26, 42)...[/bold]")
            elif title:
                titles = list(title)
                console.print(
                    f"[bold]Downloading USC title(s): {', '.join(map(str, titles))}[/bold]"
                )
            else:
                titles = [26]  # Default to Title 26 (Tax Code)
                console.print("[bold]No titles specified, downloading Title 26 (Tax Code)[/bold]")

            # Download schema files first
            await downloader.download_schema_files()

            # Download USC titles
            start_time = time.time()
            downloaded = await downloader.download_titles(titles, update_catalog=False, force=force)
            elapsed = time.time() - start_time

            console.print(
                f"\n[bold green]Downloaded {len(downloaded)} titles in {elapsed:.1f} seconds[/bold green]"
            )

            # Write download summary
            summary_file = Path(data_dir) / "download_summary.txt"
            with open(summary_file, "w") as f:
                f.write("USC Download Summary\n")
                f.write("===================\n")
                f.write(f"Date: {datetime.now().isoformat()}\n")
                f.write(f"Downloaded: {len(downloaded)} titles\n")
                f.write(f"Time: {elapsed:.1f} seconds\n")
                f.write("Files:\n")
                for filepath in downloaded:
                    f.write(f"  - {filepath.name}\n")

    asyncio.run(run())


if __name__ == "__main__":
    main()
