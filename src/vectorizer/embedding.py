"""
Text embedding module
Converts text to embeddings using Claude API or open-source models
"""

import logging
import re
from typing import List, Dict, Optional
import hashlib
from bs4 import BeautifulSoup

from src.config import settings
from src.vectorizer.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Splits text into chunks using hybrid strategy:
    1. First tries to extract semantic sections (h2, h3 boundaries)
    2. For large sections, applies overlap-based chunking
    3. Preserves hierarchy and context
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

    def chunk_html(self, html: str, metadata: Dict = None) -> List[Dict]:
        """
        Chunk HTML content using hybrid semantic + overlap strategy
        Args:
            html: HTML content
            metadata: Metadata (url, title, etc)
        Returns:
            List of chunks with metadata
        """
        # Step 1: Clean HTML (remove script, style, nav, etc)
        soup = BeautifulSoup(html, "html.parser")
        self._clean_html(soup)

        # Step 2: Extract main content area
        main_content = self._extract_main_content(soup)
        if not main_content:
            logger.warning("Could not extract main content from HTML")
            return []

        # Step 3: Get all text from main content (simpler approach)
        full_text = main_content.get_text()

        # Step 4: Clean whitespace
        full_text = self._clean_text(full_text)

        if not full_text.strip():
            return []

        # Step 5: Apply smart chunking with overlap
        # This is more effective than trying to parse structure that may not exist
        chunks = self.chunk_text(full_text, metadata)

        return chunks

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chunk plain text with overlap strategy
        (backward compatible)
        Args:
            text: Plain text to chunk
            metadata: Metadata to attach to each chunk
        Returns:
            List of chunks with metadata
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
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

    def _clean_html(self, soup):
        """Remove noise from HTML"""
        for tag in soup(["script", "style", "meta", "noscript", "nav", "footer", "header"]):
            tag.decompose()

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove multiple spaces/newlines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return " ".join(chunk for chunk in chunks if chunk)

    def _extract_main_content(self, soup) -> Optional[BeautifulSoup]:
        """Extract main content area from HTML"""
        # Try to find <main> tag first
        main = soup.find("main")
        if main:
            return main

        # Fallback: look for article or large content div
        article = soup.find("article")
        if article:
            return article

        # Fallback: find div with content-like class
        content_div = soup.find("div", class_=re.compile(r"content|main|body|container"))
        if content_div:
            return content_div

        # Last resort: return body
        return soup.find("body")

    def _parse_semantic_sections(self, content) -> List[Dict]:
        """
        Parse HTML content into semantic sections
        Uses multiple strategies:
        1. Look for h2/h3 headers as section boundaries
        2. If no headers, use divs with semantic classes as sections
        3. If still nothing, return whole content as one section
        """
        sections = []

        # Strategy 1: Look for headers (h2, h3)
        headers = content.find_all(["h2", "h3"])
        if headers and len(headers) > 1:
            current_section = {"title": "", "text": "", "level": "body"}

            for element in content.descendants:
                if isinstance(element, str):
                    continue

                tag_name = getattr(element, "name", None)

                if tag_name in ["h2", "h3"]:
                    if current_section["text"].strip():
                        sections.append(current_section)

                    current_section = {
                        "title": element.get_text().strip(),
                        "text": "",
                        "level": tag_name,
                    }
                elif tag_name in ["p", "ul", "ol", "li", "span", "div"]:
                    text = element.get_text().strip()
                    if text and len(text) > 10:  # Ignore very short text
                        current_section["text"] += " " + text

            if current_section["text"].strip():
                sections.append(current_section)

        # Strategy 2: Look for semantic divs
        if not sections:
            semantic_divs = content.find_all(
                "div",
                class_=re.compile(r"section|block|content|item|card", re.IGNORECASE)
            )
            if semantic_divs:
                for div in semantic_divs:
                    title = ""
                    # Try to find title in h2/h3 within div
                    h = div.find(["h2", "h3"])
                    if h:
                        title = h.get_text().strip()

                    text = div.get_text().strip()
                    if text:
                        sections.append({
                            "title": title,
                            "text": text,
                            "level": "div"
                        })

        # Strategy 3: No structure found, return whole content
        if not sections:
            text = content.get_text().strip()
            if text:
                sections.append({
                    "title": "Content",
                    "text": text,
                    "level": "body"
                })

        logger.info(f"Parsed {len(sections)} semantic sections")
        return sections

    def _chunk_section(self, section: Dict, metadata: Dict) -> List[Dict]:
        """
        Convert a semantic section into chunks
        If large, apply overlap chunking. If small, keep intact.
        """
        chunks = []
        section_text = section["text"].strip()

        if not section_text:
            return chunks

        section_title = section["title"]
        section_level = section["level"]

        # If section is small, keep it as one chunk
        if len(section_text) <= self.chunk_size:
            chunk_id = self._generate_id(section_text, metadata)
            return [
                {
                    "id": chunk_id,
                    "content": section_text,
                    "metadata": {
                        **(metadata or {}),
                        "section_title": section_title,
                        "section_level": section_level,
                        "chunk_index": 0,
                    },
                }
            ]

        # If section is large, apply overlap chunking
        start = 0
        chunk_index = 0

        while start < len(section_text):
            end = start + self.chunk_size
            chunk_text = section_text[start:end].strip()

            if chunk_text:
                chunk_id = self._generate_id(chunk_text, metadata)
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "section_title": section_title,
                            "section_level": section_level,
                            "chunk_index": chunk_index,
                        },
                    }
                )
                chunk_index += 1

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
        Uses hybrid chunking strategy
        Args:
            pages: List of scraped pages with 'url', 'title', 'content'
        Returns:
            Total number of chunks indexed
        """
        logger.info(f"Processing {len(pages)} pages for vectorization")
        all_chunks = []

        for page in pages:
            # Get content (plain text from scraper)
            content = page.get("content", "")

            # Try HTML chunking if content looks like HTML
            if content.startswith("<"):
                chunks = self.chunker.chunk_html(
                    html=content,
                    metadata={
                        "url": page["url"],
                        "title": page.get("title", "Unknown"),
                    },
                )
            else:
                # Fallback to text chunking
                chunks = self.chunker.chunk_text(
                    text=content,
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
