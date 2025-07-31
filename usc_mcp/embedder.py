"""
VoyageAI Embedder for USC text

Handles embedding generation using VoyageAI's legal-optimized models.
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

import voyageai
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from dotenv import load_dotenv
import tiktoken

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding operation"""

    chunk_id: str
    embedding: List[float]
    metadata: Dict[str, Any]
    token_count: int


@dataclass
class ContextualizedEmbeddingResult:
    """Result of contextualized embedding operation"""

    document_id: str
    chunk_embeddings: List[EmbeddingResult]
    total_tokens: int


class VoyageEmbedder:
    """Handles embedding generation using VoyageAI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        embedding_model: str = "voyage-law-2",
        context_model: str = "voyage-context-3",
        rerank_model: str = "rerank-2",
        batch_size: int = 25,
        use_contextualized: bool = True,
        context_dimension: int = 1024,
        max_context_tokens: int = 20000,
    ):  # Reduced from 30k to 20k for safety
        """
        Initialize VoyageAI embedder

        Args:
            api_key: VoyageAI API key (defaults to env var)
            embedding_model: Model to use for standard embeddings
            context_model: Model to use for contextualized embeddings
            rerank_model: Model to use for reranking
            batch_size: Number of texts to embed at once
            use_contextualized: Whether to use contextualized embeddings
            context_dimension: Output dimension for context embeddings (256, 512, 1024, 2048)
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VoyageAI API key not found. Set VOYAGE_API_KEY environment variable.")

        self.embedding_model = embedding_model
        self.context_model = context_model
        self.rerank_model = rerank_model
        self.batch_size = batch_size
        self.use_contextualized = use_contextualized
        self.context_dimension = context_dimension
        self.max_context_tokens = int(
            os.getenv("MAX_CONTEXT_TOKENS", max_context_tokens)
        )  # Leave buffer for voyage-context-3's 32k limit

        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Initialize client
        self.client = voyageai.Client(api_key=self.api_key)

        # Get config from environment with defaults
        self.use_contextualized = (
            os.getenv("USE_CONTEXTUALIZED_EMBEDDINGS", str(use_contextualized)).lower() == "true"
        )
        self.context_model = os.getenv("VOYAGE_CONTEXT_MODEL", context_model)
        self.context_dimension = int(os.getenv("VOYAGE_CONTEXT_DIMENSION", str(context_dimension)))

        active_model = self.context_model if self.use_contextualized else self.embedding_model
        logger.info(
            f"Initialized VoyageAI embedder with model: {active_model} (contextualized: {self.use_contextualized})"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def embed_texts(self, texts: List[str], input_type: str = "document") -> Any:
        """
        Embed a batch of texts with retry logic

        Args:
            texts: List of texts to embed
            input_type: Type of input ("document" or "query")

        Returns:
            EmbeddingsObject with embeddings and token count
        """
        try:
            result = self.client.embed(texts, model=self.embedding_model, input_type=input_type)
            return result
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise

    def embed_chunks(
        self, chunks: List[Dict[str, Any]], show_progress: bool = True
    ) -> List[EmbeddingResult]:
        """
        Embed a list of text chunks

        Args:
            chunks: List of chunks with 'id', 'text', and 'metadata'
            show_progress: Whether to show progress bar

        Returns:
            List of EmbeddingResult objects
        """
        results = []
        total_tokens = 0

        # Process in batches
        batches = [chunks[i : i + self.batch_size] for i in range(0, len(chunks), self.batch_size)]

        iterator = tqdm(batches, desc="Generating embeddings") if show_progress else batches

        for batch in iterator:
            # Extract texts and metadata
            texts = [chunk["text"] for chunk in batch]

            # Generate embeddings
            embeddings_obj = self.embed_texts(texts)

            # Create results
            for i, (chunk, embedding) in enumerate(zip(batch, embeddings_obj.embeddings)):
                result = EmbeddingResult(
                    chunk_id=chunk["id"],
                    embedding=embedding,
                    metadata=chunk["metadata"],
                    token_count=len(texts[i].split()) * 2,  # Rough estimate
                )
                results.append(result)

            total_tokens += embeddings_obj.total_tokens

            # Rate limiting pause (use time.sleep instead of asyncio in sync context)
            if len(batches) > 1:
                time.sleep(0.5)

        logger.info(f"Generated {len(results)} embeddings using {total_tokens} tokens")
        return results

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query for search

        Args:
            query: Query text

        Returns:
            Query embedding vector
        """
        if self.use_contextualized:
            # For contextualized embeddings, queries are single-element lists
            result = self.contextualized_embed(inputs=[[query]], input_type="query")
            return result.results[0].embeddings[0]
        else:
            result = self.embed_texts([query], input_type="query")
            return result.embeddings[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def rerank_results(self, query: str, documents: List[str], top_k: Optional[int] = None) -> Any:
        """
        Rerank search results for better relevance

        Args:
            query: Search query
            documents: List of document texts
            top_k: Number of top results to return

        Returns:
            RerankingObject with reranked results
        """
        try:
            result = self.client.rerank(query, documents, model=self.rerank_model, top_k=top_k)
            return result
        except Exception as e:
            logger.error(f"Error reranking results: {e}")
            raise

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings

        VoyageAI embeddings are normalized, so dot product = cosine similarity
        """
        return sum(a * b for a, b in zip(embedding1, embedding2))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def contextualized_embed(self, inputs: List[List[str]], input_type: str = "document") -> Any:
        """
        Create contextualized embeddings where chunks encode context from other chunks

        Args:
            inputs: List of documents, where each document is a list of chunks
            input_type: Type of input ("document" or "query")

        Returns:
            ContextualizedEmbeddingsObject with embeddings preserving document context
        """
        try:
            result = self.client.contextualized_embed(
                inputs=inputs,
                model=self.context_model,
                input_type=input_type,
                output_dimension=self.context_dimension,
            )
            return result
        except Exception as e:
            logger.error(f"Error creating contextualized embeddings: {e}")
            raise

    async def embed_chunks_async(
        self, chunks: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[EmbeddingResult]:
        """
        Embed chunks asynchronously for better performance

        Args:
            chunks: List of chunks to embed
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of EmbeddingResult objects
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def embed_batch(batch):
            async with semaphore:
                # Run synchronous embed in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    texts = [chunk["text"] for chunk in batch]
                    embeddings_obj = await loop.run_in_executor(executor, self.embed_texts, texts)

                    # Create results
                    batch_results = []
                    for i, (chunk, embedding) in enumerate(zip(batch, embeddings_obj.embeddings)):
                        result = EmbeddingResult(
                            chunk_id=chunk["id"],
                            embedding=embedding,
                            metadata=chunk["metadata"],
                            token_count=len(texts[i].split()) * 2,
                        )
                        batch_results.append(result)

                    return batch_results

        # Create batches
        batches = [chunks[i : i + self.batch_size] for i in range(0, len(chunks), self.batch_size)]

        # Process all batches concurrently
        tasks = [embed_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

        # Flatten results
        for batch_result in batch_results:
            results.extend(batch_result)

        return results

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.tokenizer.encode(text))

    def split_large_document(self, doc_chunks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Split a document into smaller sub-documents if it exceeds token limit

        Args:
            doc_chunks: List of chunks in a document

        Returns:
            List of sub-documents, each within token limit
        """
        sub_documents = []
        current_subdoc = []
        current_tokens = 0

        # Use 80% of max tokens to leave buffer for VoyageAI's own overhead
        safe_limit = int(self.max_context_tokens * 0.8)

        for chunk in doc_chunks:
            chunk_tokens = self.count_tokens(chunk["text"])

            # Skip chunks that are too large on their own
            if chunk_tokens > safe_limit:
                logger.warning(
                    f"Chunk exceeds safe limit ({chunk_tokens} > {safe_limit}), skipping: {chunk['id']}"
                )
                continue

            # If adding this chunk would exceed limit, start new sub-document
            if current_subdoc and current_tokens + chunk_tokens > safe_limit:
                sub_documents.append(current_subdoc)
                current_subdoc = [chunk]
                current_tokens = chunk_tokens
            else:
                current_subdoc.append(chunk)
                current_tokens += chunk_tokens

        # Add final sub-document
        if current_subdoc:
            sub_documents.append(current_subdoc)

        return sub_documents

    def embed_document_chunks(
        self, document_chunks: List[List[Dict[str, Any]]], show_progress: bool = True
    ) -> List[ContextualizedEmbeddingResult]:
        """
        Embed documents with their chunks using contextualized embeddings

        Args:
            document_chunks: List of documents, each containing list of chunks
            show_progress: Whether to show progress bar

        Returns:
            List of ContextualizedEmbeddingResult objects
        """
        if not self.use_contextualized:
            # Fallback to standard embeddings if contextualized is disabled
            all_results = []
            for doc_chunks in document_chunks:
                results = self.embed_chunks(doc_chunks, show_progress=False)
                all_results.extend(results)
            return all_results

        results = []
        total_tokens = 0

        # Process each document
        iterator = (
            tqdm(document_chunks, desc="Processing documents") if show_progress else document_chunks
        )

        for doc_idx, doc_chunks in enumerate(iterator):
            # Skip empty documents
            if not doc_chunks:
                continue

            # Check document size and split if necessary
            doc_text = " ".join(chunk["text"] for chunk in doc_chunks)
            doc_tokens = self.count_tokens(doc_text)

            if doc_tokens > self.max_context_tokens:
                logger.warning(
                    f"Document {doc_idx} has {doc_tokens} tokens, splitting into sub-documents"
                )
                logger.debug(f"Document has {len(doc_chunks)} chunks")
                sub_documents = self.split_large_document(doc_chunks)
                logger.info(f"Split into {len(sub_documents)} sub-documents")

                # Process each sub-document
                for sub_idx, subdoc_chunks in enumerate(sub_documents):
                    sub_result = self._process_single_document(
                        subdoc_chunks,
                        f"{doc_chunks[0].get('metadata', {}).get('document_id', f'doc_{doc_idx}')}_{sub_idx}",
                    )
                    if sub_result:
                        results.append(sub_result)
                        total_tokens += sub_result.total_tokens
            else:
                # Process normally if within limits
                result = self._process_single_document(
                    doc_chunks,
                    doc_chunks[0].get("metadata", {}).get("document_id", f"doc_{doc_idx}"),
                )
                if result:
                    results.append(result)
                    total_tokens += result.total_tokens

        logger.info(
            f"Generated contextualized embeddings for {len(results)} documents using {total_tokens} tokens"
        )
        return results

    def _process_single_document(
        self, doc_chunks: List[Dict[str, Any]], doc_id: str
    ) -> Optional[ContextualizedEmbeddingResult]:
        """
        Process a single document's chunks into contextualized embeddings
        """
        # Extract texts for this document
        chunk_texts = [chunk["text"] for chunk in doc_chunks]

        if not chunk_texts:
            return None

        # Debug: check total tokens
        total_tokens = sum(self.count_tokens(text) for text in chunk_texts)
        logger.debug(
            f"Processing document {doc_id} with {len(chunk_texts)} chunks, {total_tokens} total tokens"
        )

        if total_tokens > self.max_context_tokens:
            logger.error(
                f"Document {doc_id} still exceeds token limit after splitting: {total_tokens} tokens"
            )
            return None

        try:
            # Create contextualized embeddings for this document
            embeddings_obj = self.contextualized_embed(
                inputs=[chunk_texts], input_type="document"  # Single document with multiple chunks
            )

            # Process results
            if embeddings_obj.results:
                result = embeddings_obj.results[0]

                # Create embedding results for each chunk
                chunk_embeddings = []
                for i, (chunk, embedding) in enumerate(zip(doc_chunks, result.embeddings)):
                    emb_result = EmbeddingResult(
                        chunk_id=chunk["id"],
                        embedding=embedding,
                        metadata=chunk["metadata"],
                        token_count=self.count_tokens(chunk["text"]),
                    )
                    chunk_embeddings.append(emb_result)

                # Create contextualized result
                ctx_result = ContextualizedEmbeddingResult(
                    document_id=doc_id,
                    chunk_embeddings=chunk_embeddings,
                    total_tokens=sum(e.token_count for e in chunk_embeddings),
                )
                return ctx_result
        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            return None

        return None

    def estimate_cost(self, num_chunks: int, avg_chunk_size: int = 500) -> Dict[str, float]:
        """
        Estimate embedding costs

        Args:
            num_chunks: Number of chunks to embed
            avg_chunk_size: Average size of chunks in tokens

        Returns:
            Dict with cost estimates
        """
        total_tokens = num_chunks * avg_chunk_size

        # VoyageAI pricing (approximate - check current rates)
        if self.use_contextualized:
            embedding_rate = 0.00012  # per 1K tokens for voyage-context-3
            model_name = self.context_model
        else:
            embedding_rate = 0.00012  # per 1K tokens for voyage-law-2
            model_name = self.embedding_model

        embedding_cost = (total_tokens / 1000) * embedding_rate

        return {
            "model": model_name,
            "total_tokens": total_tokens,
            "embedding_cost": embedding_cost,
            "total_cost": embedding_cost,
            "contextualized": self.use_contextualized,
        }
