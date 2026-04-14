#!/usr/bin/env python3
"""
Test script para probar el scraper con BBVA
Uso: python scripts/test_scraper.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.web_scraper import WebScraper
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_scraper():
    """Test scraper with configured URL"""
    logger.info(f"Testing scraper with URL: {settings.bank_website_url}")

    scraper = WebScraper()

    # Step 1: Get sitemap URLs
    logger.info("Step 1: Fetching sitemap URLs...")
    urls = scraper.get_sitemap_urls()
    logger.info(f"Found {len(urls)} URLs to scrape")

    if len(urls) > 10:
        logger.info(f"Limiting to first 10 URLs for testing")
        urls = urls[:10]

    # Step 2: Scrape each URL
    logger.info("Step 2: Scraping pages...")
    pages = []
    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] Scraping {url}")
        result = scraper.scrape_url(url)
        if result:
            pages.append(result)
            logger.info(f"  ✓ Extracted {len(result['content'])} characters")
        else:
            logger.warning(f"  ✗ Failed to scrape")

    logger.info(f"\nResults:")
    logger.info(f"  Total pages scraped: {len(pages)}")
    logger.info(f"  Total content size: {sum(len(p['content']) for p in pages)} characters")

    # Step 3: Show sample
    if pages:
        logger.info(f"\nSample from first page:")
        logger.info(f"  Title: {pages[0]['title']}")
        logger.info(f"  URL: {pages[0]['url']}")
        logger.info(f"  Content preview: {pages[0]['content'][:200]}...")

    return pages


if __name__ == "__main__":
    try:
        pages = test_scraper()
        print(f"\n✅ Scraper test completed successfully!")
        print(f"Scraped {len(pages)} pages ready for vectorization")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
