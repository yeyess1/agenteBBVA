"""
Text embedding module
Converts text to embeddings using Claude API or open-source models
"""

import logging
from typing import List, Dict
import hashlib
from src.config import settings
from src.vectorizer.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Splits text into overlapping chunks
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        Initialize chunker
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into overlapping chunks
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk (url, title, etc.)
        Returns:
            List of chunks with metadata
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                # Generate unique ID based on content hash
                chunk_id = self._generate_id(chunk_text, metadata)

                chunk = {
                    "id": chunk_id,
                    "content": chunk_text,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "chunk_start": start,
                        "chunk_end": end,
                    },
                }
                chunks.append(chunk)

            start += self.chunk_size - self.chunk_overlap

        return chunks

    @staticmethod
    def _generate_id(content: str, metadata: Dict = None) -> str:
        """
        Generate unique ID for chunk
        Args:
            content: Chunk content
            metadata: Chunk metadata
        Returns:
            Unique ID string
        """
        source = metadata.get("url", "") if metadata else ""
        chunk_hash = hashlib.md5(f"{source}:{content[:100]}".encode()).hexdigest()
        return f"chunk_{chunk_hash}"


class EmbeddingManager:
    """
    Manages text embedding and vectorization
    """

    def __init__(self):
        """Initialize embedding manager"""
        self.chunker = TextChunker()
        self.vector_store = ChromaStore()

    def process_and_index(self, pages: List[Dict]) -> int:
        """
        Process pages, chunk them, and index in vector store
        Args:
            pages: List of scraped pages with 'url', 'title', 'content'
        Returns:
            Total number of chunks indexed
        """
        logger.info(f"Processing {len(pages)} pages for vectorization")
        all_chunks = []

        for page in pages:
            chunks = self.chunker.chunk_text(
                text=page["content"],
                metadata={
                    "url": page["url"],
                    "title": page.get("title", "Unknown"),
                },
            )
            all_chunks.extend(chunks)
            logger.info(f"Created {len(chunks)} chunks from {page['url']}")

        if all_chunks:
            added_count = self.vector_store.add_documents(all_chunks)
            logger.info(f"Successfully indexed {added_count} chunks")
            return added_count

        return 0

    def search_similar(self, query: str) -> List[Dict]:
        """
        Search for documents similar to query
        Args:
            query: Query text
        Returns:
            List of similar documents with scores
        """
        logger.info(f"Searching for similar documents to: {query[:50]}...")
        results = self.vector_store.search(query, n_results=settings.retrieval_top_k)
        logger.info(f"Found {len(results)} relevant documents")
        return results

    def get_stats(self) -> Dict:
        """Get statistics about indexed content"""
        return self.vector_store.get_stats()
