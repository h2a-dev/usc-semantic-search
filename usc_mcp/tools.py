"""
MCP Tools for USC Semantic Search

Defines the tools exposed by the FastMCP server for AI agents.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from .database import ChromaDatabase
from .embedder import VoyageEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from semantic search"""

    citation: str
    title: str
    section_name: str
    text: str
    score: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CitationResult:
    """Result from citation lookup"""

    citation: str
    title: str
    section_name: str
    full_text: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrowseResult:
    """Result from hierarchical browsing"""

    level: str  # "titles", "chapters", "sections"
    items: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class USCSearchTools:
    """Tools for searching and accessing USC content"""

    def __init__(self, database: ChromaDatabase, embedder: VoyageEmbedder):
        self.database = database
        self.embedder = embedder

    async def search_usc(
        self, query: str, limit: int = 10, title: Optional[int] = None, rerank: bool = True
    ) -> List[SearchResult]:
        """
        Semantic search across US Code

        Args:
            query: Natural language search query
            limit: Maximum number of results
            title: Optional title number to filter by
            rerank: Whether to use reranking for better results

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Searching USC for: {query}")

        # Embed the query
        query_embedding = self.embedder.embed_query(query)

        # Prepare filters
        filter_dict = {}
        if title is not None:
            filter_dict["title_num"] = str(title)

        # Search database
        search_results = self.database.search(
            query_embedding=query_embedding,
            limit=limit * 2 if rerank else limit,  # Get more results if reranking
            filter_dict=filter_dict,
        )

        # If reranking is enabled, rerank the results
        if rerank and len(search_results) > 1:
            # Get full texts for reranking
            documents = []
            for result in search_results:
                # Get the actual section text from database
                section = self.database.get_by_id(result["id"])
                if section:
                    # Reconstruct full text from metadata
                    text_parts = [
                        result["metadata"].get("heading", ""),
                        result["metadata"].get("text", ""),
                        result["document"],
                    ]
                    documents.append("\n".join(filter(None, text_parts)))
                else:
                    documents.append(result["document"])

            # Rerank
            rerank_results = self.embedder.rerank_results(
                query=query, documents=documents, top_k=limit
            )

            # Reorder results based on reranking
            reranked_search_results = []
            for rerank_result in rerank_results.results:
                original_result = search_results[rerank_result.index]
                original_result["score"] = rerank_result.relevance_score
                reranked_search_results.append(original_result)

            search_results = reranked_search_results
        else:
            search_results = search_results[:limit]

        # Format results
        results = []
        for result in search_results:
            metadata = result["metadata"]

            # Get full section text
            section = self.database.get_by_id(result["id"])
            text = result["document"]
            if section and "text" in metadata:
                text = metadata.get("text", text)

            # Fix section name - use heading if section_name is empty
            section_name = metadata.get("section_name", "") or metadata.get("heading", "")

            search_result = SearchResult(
                citation=metadata.get("full_citation", ""),
                title=f"Title {metadata.get('title_num', '')} - {metadata.get('title_name', '')}",
                section_name=section_name,
                text=text[:500] + "..." if len(text) > 500 else text,  # Truncate for display
                score=result["score"],
                metadata={
                    "section_id": result["id"],
                    "chapter": metadata.get("chapter_name", ""),
                    "has_notes": str(metadata.get("has_notes", False)).lower() == "true",
                    "has_amendments": str(metadata.get("has_amendments", False)).lower() == "true",
                },
            )
            results.append(search_result)

        logger.info(f"Found {len(results)} results for query: {query}")
        return results

    async def get_citation(self, citation: str) -> Optional[CitationResult]:
        """
        Retrieve specific USC section by citation

        Args:
            citation: Legal citation (e.g., "26 USC 1001" or "26 § 1001")

        Returns:
            CitationResult or None if not found
        """
        logger.info(f"Looking up citation: {citation}")

        # Try direct lookup first (exact match)
        logger.debug(f"Trying direct citation lookup: {citation}")
        result = self.database.get_by_citation(citation)

        if not result:
            # Try searching by ID format
            # Handle formats like "7 USC § 1511." or "26 USC 1001" or "7 USC 2012"
            import re

            # Normalize the citation first
            normalized = citation.strip()
            logger.debug(f"Normalized citation: {normalized}")

            # Add § if missing between USC and number
            if "USC" in normalized and "§" not in normalized:
                normalized = normalized.replace("USC", "USC §")
                logger.debug(f"Added § symbol: {normalized}")

            # Extract title and section number
            match = re.match(r"(\d+)\s+USC\s+§?\s*([^\s.]+)", normalized)
            if match:
                title = match.group(1)
                section = match.group(2)
                logger.debug(f"Extracted title={title}, section={section}")

                # Try multiple ID formats as they appear in the database
                id_formats = [
                    f"{title}-§ {section}.",  # With § and period (most common)
                    f"{title}-§ {section}",  # With § no period
                    f"{title}-{section}.",  # No § with period
                    f"{title}-{section}",  # No § no period
                ]

                for section_id in id_formats:
                    logger.debug(f"Trying ID format: {section_id}")
                    result = self.database.get_by_id(section_id)
                    if result:
                        logger.info(f"Found citation with ID: {section_id}")
                        break
                    else:
                        logger.debug(f"Not found with ID: {section_id}")
            else:
                logger.warning(f"Could not parse citation format: {normalized}")

        if result:
            metadata = result["metadata"]

            # Get full text
            full_text = metadata.get("text", result["document"])

            return CitationResult(
                citation=metadata.get("full_citation", citation),
                title=f"Title {metadata.get('title_num', '')} - {metadata.get('title_name', '')}",
                section_name=metadata.get("section_name", ""),
                full_text=full_text,
                metadata={
                    "section_id": result["id"],
                    "chapter": metadata.get("chapter_name", ""),
                    "source_credit": metadata.get("source_credit", ""),
                    "effective_date": metadata.get("effective_date", ""),
                    "has_notes": metadata.get("has_notes", "false") == "true",
                    "has_amendments": metadata.get("has_amendments", "false") == "true",
                },
            )

        logger.warning(f"Citation not found: {citation}")
        return None

    async def browse_usc(
        self, title: Optional[int] = None, chapter: Optional[int] = None
    ) -> BrowseResult:
        """
        Browse USC hierarchy

        Args:
            title: Optional title number
            chapter: Optional chapter number

        Returns:
            BrowseResult with hierarchical listing
        """
        if title is None:
            # Return list of titles
            stats = self.database.get_stats()
            items = []

            for title_num in stats["titles"]:
                # Get sample section to get title name
                sections = self.database.browse_hierarchy(title_num=title_num)
                if sections:
                    title_name = sections[0]["metadata"].get("title_name", "")
                    items.append({"number": title_num, "name": title_name, "type": "title"})

            return BrowseResult(level="titles", items=items)

        elif chapter is None:
            # Return chapters in a title
            sections = self.database.browse_hierarchy(title_num=str(title))

            # Extract unique chapters
            chapters = {}
            for section in sections:
                ch_num = section["metadata"].get("chapter_num")
                ch_name = section["metadata"].get("chapter_name")
                if ch_num and ch_num not in chapters:
                    chapters[ch_num] = ch_name

            items = [
                {"number": ch_num, "name": ch_name or "", "type": "chapter"}
                for ch_num, ch_name in sorted(chapters.items())
            ]

            return BrowseResult(level="chapters", items=items)

        else:
            # Return sections in a chapter
            sections = self.database.browse_hierarchy(
                title_num=str(title), chapter_num=str(chapter)
            )

            items = [
                {
                    "number": section["metadata"].get("section_num", ""),
                    "name": section["metadata"].get("section_name", ""),
                    "type": "section",
                    "citation": section["metadata"].get("full_citation", ""),
                }
                for section in sections
            ]

            return BrowseResult(level="sections", items=items)

    async def get_context(self, section_id: str, context_size: int = 2) -> List[CitationResult]:
        """
        Get surrounding sections for context

        Args:
            section_id: Section ID (e.g., "26-1001")
            context_size: Number of sections before/after

        Returns:
            List of sections including target and context
        """
        # Get the target section
        target = self.database.get_by_id(section_id)
        if not target:
            return []

        # Get sections from same chapter
        title_num = target["metadata"].get("title_num")
        chapter_num = target["metadata"].get("chapter_num")

        if not title_num:
            return []

        sections = self.database.browse_hierarchy(title_num=title_num, chapter_num=chapter_num)

        # Find target index
        target_idx = None
        for i, section in enumerate(sections):
            if section["id"] == section_id:
                target_idx = i
                break

        if target_idx is None:
            return []

        # Get context range
        start_idx = max(0, target_idx - context_size)
        end_idx = min(len(sections), target_idx + context_size + 1)

        # Get full details for context sections
        results = []
        for i in range(start_idx, end_idx):
            section_data = self.database.get_by_id(sections[i]["id"])
            if section_data:
                metadata = section_data["metadata"]
                result = CitationResult(
                    citation=metadata.get("full_citation", ""),
                    title=f"Title {metadata.get('title_num', '')}",
                    section_name=metadata.get("section_name", ""),
                    full_text=metadata.get("text", section_data["document"]),
                    metadata={"is_target": sections[i]["id"] == section_id},
                )
                results.append(result)

        return results
