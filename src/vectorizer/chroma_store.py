"""
Chroma DB vector store module
Manages embeddings storage and retrieval
"""

import logging
from typing import List, Dict, Optional
import chromadb

from src.config import settings

logger = logging.getLogger(__name__)


class ChromaStore:
    """
    Vector store using Chroma DB
    Manages embeddings and semantic search
    """

    def __init__(self):
        """Initialize Chroma DB connection"""
        # Use new Chroma client with persistent storage
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: List[Dict]) -> int:
        """
        Add documents to vector store
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
        Returns:
            Number of documents added
        """
        try:
            ids = []
            documents_content = []
            metadatas = []

            for doc in documents:
                ids.append(doc["id"])
                documents_content.append(doc["content"])
                metadatas.append(doc.get("metadata", {}))

            self.collection.add(
                ids=ids,
                documents=documents_content,
                metadatas=metadatas,
            )

            logger.info(f"Added {len(documents)} documents to vector store")
            return len(documents)
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def search(self, query: str, n_results: int = None) -> List[Dict]:
        """
        Search for relevant documents
        Args:
            query: Query text
            n_results: Number of results to return (defaults to RETRIEVAL_TOP_K)
        Returns:
            List of documents with distance scores
        """
        n_results = n_results or settings.retrieval_top_k

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
            )

            # Format results
            documents = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })

            return documents
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

    def delete_all(self) -> bool:
        """
        Delete all documents from collection
        (Use with caution!)
        Returns:
            True if successful
        """
        try:
            # Get all documents
            all_docs = self.collection.get()
            if all_docs["ids"]:
                self.collection.delete(ids=all_docs["ids"])
                logger.warning(f"Deleted {len(all_docs['ids'])} documents from vector store")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get collection statistics
        Returns:
            Dict with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "collection": settings.chroma_collection,
                "document_count": count,
                "persist_directory": settings.chroma_persist_directory,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

    def persist(self):
        """Persist collection to disk (automatic with PersistentClient)"""
        logger.info("Vector store persistence is automatic with PersistentClient")
