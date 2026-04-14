#!/usr/bin/env python3
"""
Script para scraper, chunkear e indexar contenido en Chroma DB
Uso: python scripts/index_content.py [--limit N]

Ejemplo:
  python scripts/index_content.py              # Indexa todas las URLs
  python scripts/index_content.py --limit 50   # Indexa solo 50 URLs
"""

import sys
import logging
import argparse
from pathlib import Path
from time import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.web_scraper import WebScraper
from src.vectorizer.embedding import EmbeddingManager
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(limit: int = None):
    """
    Main indexing pipeline
    Args:
        limit: Limit number of URLs to scrape (for testing)
    """
    start_time = time()

    logger.info("=" * 80)
    logger.info("BBVA Content Indexing Pipeline")
    logger.info("=" * 80)

    # Step 1: Get URLs from sitemap
    logger.info("\n[STEP 1] Fetching sitemap URLs...")
    scraper = WebScraper()
    urls = scraper.get_sitemap_urls()
    logger.info(f"Total URLs found: {len(urls)}")

    if limit:
        logger.info(f"Limiting to {limit} URLs")
        urls = urls[:limit]

    # Step 2: Scrape all pages
    logger.info(f"\n[STEP 2] Scraping {len(urls)} pages...")
    pages = []
    failed_urls = []

    for i, url in enumerate(urls, 1):
        try:
            if i % 10 == 0 or i == len(urls):
                logger.info(f"  [{i}/{len(urls)}] Scraping...")

            result = scraper.scrape_url(url)
            if result:
                pages.append(result)
            else:
                failed_urls.append(url)
        except Exception as e:
            logger.warning(f"  Error scraping {url}: {e}")
            failed_urls.append(url)

    logger.info(f"\nScraping complete:")
    logger.info(f"  ✓ Successfully scraped: {len(pages)} pages")
    logger.info(f"  ✗ Failed: {len(failed_urls)} pages")

    if not pages:
        logger.error("No pages were scraped!")
        return False

    # Step 3: Vectorize and index
    logger.info(f"\n[STEP 3] Vectorizing and indexing in Chroma DB...")
    logger.info(f"  Chunk size: {settings.chunk_size}")
    logger.info(f"  Chunk overlap: {settings.chunk_overlap}")

    embedding_manager = EmbeddingManager()
    total_chunks = embedding_manager.process_and_index(pages)

    # Step 4: Get statistics
    logger.info(f"\n[STEP 4] Indexing statistics...")
    stats = embedding_manager.get_stats()
    logger.info(f"  Collection: {stats['collection']}")
    logger.info(f"  Total documents indexed: {stats['document_count']}")
    logger.info(f"  Storage location: {stats['persist_directory']}")

    # Summary
    elapsed = time() - start_time
    logger.info(f"\n" + "=" * 80)
    logger.info(f"INDEXING COMPLETE")
    logger.info(f"=" * 80)
    logger.info(f"  Pages scraped: {len(pages)}")
    logger.info(f"  Total chunks created: {total_chunks}")
    logger.info(f"  Avg chunks per page: {total_chunks / len(pages):.1f}")
    logger.info(f"  Total content indexed: {stats['document_count']} chunks")
    logger.info(f"  Time elapsed: {elapsed:.1f}s")
    logger.info(f"")
    logger.info(f"✅ Ready for semantic search!")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape, chunk, and index BBVA content in Chroma DB"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of URLs to scrape (for testing)"
    )
    args = parser.parse_args()

    try:
        success = main(limit=args.limit)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
