"""
Supabase Vector Store module
Manages embeddings storage and retrieval using pgvector
"""

import logging
from typing import List, Dict, Optional
import numpy as np
from supabase import create_client
from sentence_transformers import SentenceTransformer

from src.config import settings

logger = logging.getLogger(__name__)


class SupabaseVectorStore:
    """
    Vector store using Supabase + pgvector
    Manages embeddings and semantic search
    """

    def __init__(self):
        """Initialize Supabase connection and embedding model"""
        # Initialize Supabase client
        self.client = create_client(
            settings.supabase_url,
            settings.supabase_api_key
        )

        # Initialize BGE-M3 embedding model
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Model loaded. Embedding dimension: {self.model.get_embedding_dimension()}")

    def add_documents(self, documents: List[Dict]) -> int:
        """
        Add documents to vector store with embeddings
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
        Returns:
            Number of documents added
        """
        try:
            documents_to_insert = []

            for doc in documents:
                # Generate embedding for content
                content = doc["content"]
                embedding = self.model.encode(content, convert_to_numpy=True)

                # Prepare document for insertion
                doc_record = {
                    "chunk_id": doc["id"],
                    "content": content,
                    "embedding": embedding.tolist(),  # pgvector expects list
                    "metadata": doc.get("metadata", {}),
                    "source_url": doc.get("metadata", {}).get("url"),
                    "title": doc.get("metadata", {}).get("title"),
                }
                documents_to_insert.append(doc_record)

            # Batch insert into Supabase
            response = self.client.table("documents").insert(documents_to_insert).execute()

            logger.info(f"Added {len(documents_to_insert)} documents to Supabase vector store")
            return len(documents_to_insert)

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def search(self, query: str, n_results: int = None) -> List[Dict]:
        """
        Search for relevant documents using vector similarity
        Args:
            query: Query text
            n_results: Number of results to return
        Returns:
            List of documents with distance scores
        """
        n_results = n_results or settings.retrieval_top_k

        try:
            # Generate embedding for query
            query_embedding = self.model.encode(query, convert_to_numpy=True)

            # Search using pgvector similarity (cosine distance)
            # Using RPC function for vector search
            results = self.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding.tolist(),
                    'match_count': n_results,
                    'match_threshold': 0.0  # Return all, sorted by similarity
                }
            ).execute()

            # Format results
            documents = []
            if results.data:
                for result in results.data:
                    documents.append({
                        "content": result["content"],
                        "metadata": result.get("metadata", {}),
                        "distance": result.get("similarity", 0),
                    })

            logger.info(f"Found {len(documents)} relevant documents for query")
            return documents

        except Exception as e:
            logger.error(f"Error searching: {e}")
            # Fallback to text search if RPC not available
            return self._fallback_search(query, n_results)

    def _fallback_search(self, query: str, n_results: int) -> List[Dict]:
        """
        Fallback search using text similarity when RPC not available
        Args:
            query: Query text
            n_results: Number of results to return
        Returns:
            List of documents
        """
        try:
            # Simple text-based search as fallback
            results = self.client.table("documents").select(
                "id, content, metadata, source_url, title"
            ).ilike("content", f"%{query}%").limit(n_results).execute()

            documents = []
            if results.data:
                for result in results.data:
                    documents.append({
                        "content": result["content"],
                        "metadata": result.get("metadata", {}),
                        "distance": 0,  # No similarity score in fallback
                    })

            logger.info(f"Fallback search returned {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get collection statistics
        Returns:
            Dict with collection stats
        """
        try:
            # Count documents
            result = self.client.table("documents").select(
                "id", count="exact"
            ).execute()

            count = len(result.data) if result.data else 0

            return {
                "vector_store": "supabase_pgvector",
                "document_count": count,
                "embedding_model": settings.embedding_model,
                "vector_dimension": settings.vector_dimension,
                "supabase_url": settings.supabase_url,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
