"""
Document retriever module
Retrieves relevant documents from vector store
"""

import logging
from typing import List, Dict
from src.vectorizer.embedding import EmbeddingManager
from src.config import settings

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """
    Retrieves relevant documents from vector store
    """

    def __init__(self):
        """Initialize retriever"""
        self.embedding_manager = EmbeddingManager()

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve documents relevant to query
        Args:
            query: User query
            top_k: Number of documents to retrieve
        Returns:
            List of relevant documents with metadata
        """
        top_k = top_k or settings.retrieval_top_k
        logger.info(f"Retrieving top {top_k} documents for query: {query[:50]}...")

        results = self.embedding_manager.search_similar(query)

        if len(results) > top_k:
            results = results[:top_k]

        logger.info(f"Retrieved {len(results)} documents")
        return results

    def format_context(self, documents: List[Dict]) -> str:
        """
        Format retrieved documents for LLM context
        Args:
            documents: List of retrieved documents
        Returns:
            Formatted context string
        """
        if not documents:
            return "No relevant documents found."

        context_parts = []
        for i, doc in enumerate(documents, 1):
            url = doc.get("metadata", {}).get("url", "Unknown source")
            content = doc.get("content", "")
            context_parts.append(f"[Source {i}: {url}]\n{content}\n")

        return "\n".join(context_parts)

    def get_sources(self, documents: List[Dict]) -> List[Dict]:
        """
        Extract source information from documents
        Args:
            documents: List of retrieved documents
        Returns:
            List of unique sources
        """
        sources = {}
        for doc in documents:
            metadata = doc.get("metadata", {})
            url = metadata.get("url")
            title = metadata.get("title")

            if url and url not in sources:
                sources[url] = {"url": url, "title": title}

        return list(sources.values())
