"""
ChromaDB Database Interface for USC Semantic Search

Manages vector storage and retrieval using ChromaDB.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ChromaDatabase:
    """Manages USC sections in ChromaDB for semantic search"""

    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "usc_sections"):
        """
        Initialize ChromaDB client

        Args:
            persist_dir: Directory to persist database
            collection_name: Name of the collection
        """
        # Use absolute path to ensure we find the database regardless of working directory
        default_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "db"
        )
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", default_dir)
        self.collection_name = collection_name

        # Ensure directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_dir, settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )

        # Get or create collection
        self.collection = self._get_or_create_collection()

        logger.info(f"Initialized ChromaDB at {self.persist_dir}")
        logger.info(f"Database absolute path: {os.path.abspath(self.persist_dir)}")

        # Log initial stats for debugging
        try:
            count = self.collection.count()
            logger.info(f"Collection '{self.collection_name}' has {count} documents")
        except Exception as e:
            logger.warning(f"Could not get collection count: {e}")

    def _get_or_create_collection(self):
        """Get or create the USC sections collection"""
        try:
            # List existing collections
            existing_collections = [col.name for col in self.client.list_collections()]

            if self.collection_name in existing_collections:
                # Get existing collection
                collection = self.client.get_collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                # Create new collection
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "United States Code sections for semantic search"},
                )
                logger.info(f"Created new collection: {self.collection_name}")

            return collection

        except Exception as e:
            logger.error(f"Error with collection: {e}")
            # If there's any error, try to create a new collection
            try:
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "United States Code sections for semantic search"},
                )
                logger.info(f"Created new collection after error: {self.collection_name}")
                return collection
            except Exception as create_error:
                logger.error(f"Failed to create collection: {create_error}")
                raise

    def add_embeddings(self, embedding_results: List[Any]) -> int:
        """
        Add embeddings to the database

        Args:
            embedding_results: List of EmbeddingResult objects

        Returns:
            Number of embeddings added
        """
        if not embedding_results:
            return 0

        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for result in embedding_results:
            ids.append(result.chunk_id)
            embeddings.append(result.embedding)

            # Prepare metadata (ChromaDB requires string values)
            metadata = {}
            for key, value in result.metadata.items():
                if value is None:
                    metadata[key] = ""
                elif isinstance(value, (int, float, bool)):
                    metadata[key] = str(value)
                elif isinstance(value, list):
                    metadata[key] = json.dumps(value)
                else:
                    metadata[key] = str(value)

            metadatas.append(metadata)

            # Store the section text as document
            documents.append(
                f"{result.metadata.get('heading', '')} {result.metadata.get('full_citation', '')}"
            )

        # Add to collection
        self.collection.add(
            ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
        )

        logger.info(f"Added {len(ids)} embeddings to database")
        return len(ids)

    def add_contextualized_embeddings(self, embedding_results: List[Any]) -> int:
        """
        Add contextualized embeddings to the database

        Args:
            embedding_results: List of ContextualizedEmbeddingResult objects

        Returns:
            Number of embeddings added
        """
        if not embedding_results:
            return 0

        total_added = 0

        # Process each document's embeddings
        for ctx_result in embedding_results:
            # For contextualized embeddings, we store the chunk embeddings
            # but preserve the document relationship in metadata
            chunk_results = ctx_result.chunk_embeddings

            # Add document ID to each chunk's metadata
            for chunk_result in chunk_results:
                if "document_id" not in chunk_result.metadata:
                    chunk_result.metadata["document_id"] = ctx_result.document_id

            # Use the standard add_embeddings method
            added = self.add_embeddings(chunk_results)
            total_added += added

        logger.info(
            f"Added {total_added} contextualized embeddings from {len(embedding_results)} documents"
        )
        return total_added

    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar sections using query embedding

        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            filter_dict: Optional metadata filters

        Returns:
            List of search results with metadata and scores
        """
        # Prepare where clause for filtering
        where = {}
        if filter_dict:
            for key, value in filter_dict.items():
                if value is not None:
                    where[key] = str(value)

        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where if where else None,
            include=["metadatas", "documents", "distances"],
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "metadata": results["metadatas"][0][i],
                    "document": results["documents"][0][i],
                }

                # Parse JSON fields in metadata
                for key, value in result["metadata"].items():
                    if value.startswith("[") or value.startswith("{"):
                        try:
                            result["metadata"][key] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            pass

                formatted_results.append(result)

        return formatted_results

    def get_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific section by ID

        Args:
            section_id: Section ID (e.g., "26-1001")

        Returns:
            Section data or None if not found
        """
        try:
            results = self.collection.get(
                ids=[section_id],
                include=[
                    "metadatas",
                    "documents",
                ],  # Don't include embeddings to avoid numpy issues
            )

            if results["ids"] and len(results["ids"]) > 0:
                return {
                    "id": results["ids"][0],
                    "metadata": results["metadatas"][0],
                    "document": results["documents"][0] if results["documents"] else "",
                    "embedding": None,  # Skip embedding for now
                }

        except Exception as e:
            logger.error(f"Error getting section {section_id}: {e}")

        return None

    def get_by_citation(self, citation: str) -> Optional[Dict[str, Any]]:
        """
        Get a section by its legal citation

        Args:
            citation: Legal citation (e.g., "26 USC 1001")

        Returns:
            Section data or None if not found
        """
        # Search by full_citation metadata
        results = self.collection.get(
            where={"full_citation": citation}, include=["metadatas", "documents"]
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "metadata": results["metadatas"][0],
                "document": results["documents"][0],
            }

        return None

    def browse_hierarchy(
        self, title_num: Optional[str] = None, chapter_num: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Browse USC hierarchy

        Args:
            title_num: Title number to filter by
            chapter_num: Chapter number to filter by

        Returns:
            List of sections matching the hierarchy
        """
        # ChromaDB requires specific operator syntax for multiple conditions
        where = None
        if title_num and chapter_num:
            where = {
                "$and": [
                    {"title_num": {"$eq": str(title_num)}},
                    {"chapter_num": {"$eq": str(chapter_num)}},
                ]
            }
        elif title_num:
            where = {"title_num": {"$eq": str(title_num)}}
        elif chapter_num:
            where = {"chapter_num": {"$eq": str(chapter_num)}}

        results = self.collection.get(
            where=where, include=["metadatas"], limit=1000  # Get all matching sections
        )

        # Format and sort results
        sections = []
        for i in range(len(results["ids"])):
            sections.append({"id": results["ids"][i], "metadata": results["metadatas"][i]})

        # Sort by section number
        sections.sort(key=lambda x: x["metadata"].get("section_num", ""))

        return sections

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            count = self.collection.count()

            # Get sample to determine titles
            sample = self.collection.get(limit=1000, include=["metadatas"])

            titles = set()
            chapters = set()
            documents = set()
            embedding_type = "unknown"

            if sample["metadatas"]:
                for metadata in sample["metadatas"]:
                    if "title_num" in metadata:
                        titles.add(metadata["title_num"])
                    if "chapter_num" in metadata and metadata["chapter_num"]:
                        chapters.add(f"{metadata['title_num']}-{metadata['chapter_num']}")
                    if "document_id" in metadata:
                        documents.add(metadata["document_id"])
                        embedding_type = "contextualized"
                    elif embedding_type == "unknown":
                        embedding_type = "standard"

            return {
                "total_sections": count,
                "unique_titles": len(titles),
                "unique_chapters": len(chapters),
                "unique_documents": len(documents),
                "titles": sorted(list(titles)),
                "database_path": self.persist_dir,
                "collection_name": self.collection_name,
                "embedding_type": embedding_type,
            }
        except Exception as e:
            logger.warning(f"Error getting stats: {e}")
            return {
                "total_sections": 0,
                "unique_titles": 0,
                "unique_chapters": 0,
                "unique_documents": 0,
                "titles": [],
                "database_path": self.persist_dir,
                "collection_name": self.collection_name,
                "embedding_type": "unknown",
            }

    def clear_collection(self):
        """Clear all data from the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    def export_metadata(self, output_file: str):
        """Export all metadata to a JSON file for debugging"""
        results = self.collection.get(
            limit=self.collection.count(), include=["metadatas", "documents"]
        )

        data = []
        for i in range(len(results["ids"])):
            data.append(
                {
                    "id": results["ids"][i],
                    "metadata": results["metadatas"][i],
                    "document": results["documents"][i],
                }
            )

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(data)} records to {output_file}")
