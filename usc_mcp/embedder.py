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

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result of embedding operation"""
    chunk_id: str
    embedding: List[float]
    metadata: Dict[str, Any]
    token_count: int

class VoyageEmbedder:
    """Handles embedding generation using VoyageAI"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 embedding_model: str = "voyage-law-2",
                 rerank_model: str = "rerank-2",
                 batch_size: int = 25):
        """
        Initialize VoyageAI embedder
        
        Args:
            api_key: VoyageAI API key (defaults to env var)
            embedding_model: Model to use for embeddings
            rerank_model: Model to use for reranking
            batch_size: Number of texts to embed at once
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VoyageAI API key not found. Set VOYAGE_API_KEY environment variable.")
            
        self.embedding_model = embedding_model
        self.rerank_model = rerank_model
        self.batch_size = batch_size
        
        # Initialize client
        self.client = voyageai.Client(api_key=self.api_key)
        
        logger.info(f"Initialized VoyageAI embedder with model: {embedding_model}")
        
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
            result = self.client.embed(
                texts,
                model=self.embedding_model,
                input_type=input_type
            )
            return result
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise
            
    def embed_chunks(self, chunks: List[Dict[str, Any]], 
                    show_progress: bool = True) -> List[EmbeddingResult]:
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
        batches = [chunks[i:i + self.batch_size] for i in range(0, len(chunks), self.batch_size)]
        
        iterator = tqdm(batches, desc="Generating embeddings") if show_progress else batches
        
        for batch in iterator:
            # Extract texts and metadata
            texts = [chunk['text'] for chunk in batch]
            
            # Generate embeddings
            embeddings_obj = self.embed_texts(texts)
            
            # Create results
            for i, (chunk, embedding) in enumerate(zip(batch, embeddings_obj.embeddings)):
                result = EmbeddingResult(
                    chunk_id=chunk['id'],
                    embedding=embedding,
                    metadata=chunk['metadata'],
                    token_count=len(texts[i].split()) * 2  # Rough estimate
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
        result = self.embed_texts([query], input_type="query")
        return result.embeddings[0]
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def rerank_results(self, query: str, documents: List[str], 
                      top_k: Optional[int] = None) -> Any:
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
            result = self.client.rerank(
                query,
                documents,
                model=self.rerank_model,
                top_k=top_k
            )
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
        
    async def embed_chunks_async(self, chunks: List[Dict[str, Any]], 
                                max_concurrent: int = 5) -> List[EmbeddingResult]:
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
                    texts = [chunk['text'] for chunk in batch]
                    embeddings_obj = await loop.run_in_executor(
                        executor, 
                        self.embed_texts, 
                        texts
                    )
                    
                    # Create results
                    batch_results = []
                    for i, (chunk, embedding) in enumerate(zip(batch, embeddings_obj.embeddings)):
                        result = EmbeddingResult(
                            chunk_id=chunk['id'],
                            embedding=embedding,
                            metadata=chunk['metadata'],
                            token_count=len(texts[i].split()) * 2
                        )
                        batch_results.append(result)
                        
                    return batch_results
                    
        # Create batches
        batches = [chunks[i:i + self.batch_size] for i in range(0, len(chunks), self.batch_size)]
        
        # Process all batches concurrently
        tasks = [embed_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        for batch_result in batch_results:
            results.extend(batch_result)
            
        return results
        
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
        embedding_rate = 0.00012  # per 1K tokens for voyage-law-2
        
        embedding_cost = (total_tokens / 1000) * embedding_rate
        
        return {
            'total_tokens': total_tokens,
            'embedding_cost': embedding_cost,
            'total_cost': embedding_cost
        }