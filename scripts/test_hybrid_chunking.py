#!/usr/bin/env python3
"""
Test script para el chunking híbrido
Compara: texto plano vs HTML estructurado
Uso: python scripts/test_hybrid_chunking.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vectorizer.embedding import TextChunker
from src.scraper.web_scraper import WebScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_chunking():
    """Test hybrid chunking with real BBVA page"""
    print("\n" + "=" * 80)
    print("TESTING HYBRID CHUNKING STRATEGY")
    print("=" * 80)

    # Fetch a real page
    scraper = WebScraper()
    url = "https://www.bbva.com.co/personas/productos/prestamos/vivienda/hipotecario.html"

    logger.info(f"Fetching page: {url}")
    html = scraper.fetch_page(url)
    if not html:
        logger.error("Failed to fetch page")
        return False

    soup_obj = __import__("bs4").BeautifulSoup(html, "html.parser")
    title = soup_obj.title.string if soup_obj.title else "Unknown"

    metadata = {
        "url": url,
        "title": title,
    }

    # Initialize chunker
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)

    print("\n" + "-" * 80)
    print("STRATEGY 1: Hybrid HTML Chunking")
    print("-" * 80)

    html_chunks = chunker.chunk_html(html, metadata)
    print(f"\n✓ Created {len(html_chunks)} chunks via hybrid strategy")

    if html_chunks:
        print("\nFirst 3 chunks:")
        for i, chunk in enumerate(html_chunks[:3], 1):
            section = chunk["metadata"].get("section_title", "No section")
            level = chunk["metadata"].get("section_level", "?")
            content_preview = chunk["content"][:150].replace("\n", " ")
            print(f"\n  [{i}] <{level}> {section}")
            print(f"      Content ({len(chunk['content'])} chars): {content_preview}...")

    print("\n" + "-" * 80)
    print("STRATEGY 2: Plain Text Chunking (for comparison)")
    print("-" * 80)

    # Extract plain text
    plain_text = scraper.extract_text(html)
    text_chunks = chunker.chunk_text(plain_text, metadata)
    print(f"\n✓ Created {len(text_chunks)} chunks via plain text overlap")

    if text_chunks:
        print("\nFirst 3 chunks:")
        for i, chunk in enumerate(text_chunks[:3], 1):
            content_preview = chunk["content"][:150].replace("\n", " ")
            print(f"\n  [{i}] ({len(chunk['content'])} chars): {content_preview}...")

    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(f"\nHTML Chunking (Hybrid):")
    print(f"  Total chunks: {len(html_chunks)}")
    avg_html_size = sum(len(c['content']) for c in html_chunks) / len(html_chunks) if html_chunks else 0
    print(f"  Avg chunk size: {avg_html_size:.0f} characters")
    print(f"  Preserves: Section titles, hierarchy, semantic meaning")

    print(f"\nText Chunking (Overlap):")
    print(f"  Total chunks: {len(text_chunks)}")
    avg_text_size = sum(len(c['content']) for c in text_chunks) / len(text_chunks) if text_chunks else 0
    print(f"  Avg chunk size: {avg_text_size:.0f} characters")
    print(f"  Preserves: Just text overlap")

    print(f"\nReduction: {len(text_chunks) - len(html_chunks)} fewer chunks with hybrid ({(1 - len(html_chunks)/len(text_chunks))*100:.1f}% reduction)")

    print("\n" + "=" * 80)
    print("✅ Hybrid chunking test complete!")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = test_chunking()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
