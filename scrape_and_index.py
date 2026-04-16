#!/usr/bin/env python3
"""
Scrape BBVA website and index content in Supabase vector store.
Optimized for free tier sustainability.

Usage:
    python scrape_and_index.py [--max-urls 50]
"""

import sys
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main scraping and indexing pipeline."""
    parser = argparse.ArgumentParser(description="Scrape BBVA and index in Supabase")
    parser.add_argument(
        "--max-urls",
        type=int,
        default=50,
        help="Maximum URLs to scrape (default: 50 for free tier sustainability)"
    )
    args = parser.parse_args()

    try:
        from src.scraper.web_scraper import WebScraper
        from src.vectorizer.embedding import EmbeddingManager
    except ImportError as e:
        logger.error(f"Failed to import modules: {e}")
        logger.error("Make sure you're running from the project root directory")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🚀 BBVA Web Scraper & Vector Indexer")
    logger.info("=" * 70)

    # ── Step 1: Discover URLs ──────────────────────────────────────────────
    logger.info("\n📍 Step 1: Discovering URLs from sitemap...")
    logger.info(f"   Max URLs to scrape: {args.max_urls}")

    try:
        scraper = WebScraper()
        urls = scraper.get_sitemap_urls(max_urls=args.max_urls)
        logger.info(f"   ✅ Found {len(urls)} high-value URLs")

        if urls:
            logger.info("\n   Sample URLs:")
            for i, url in enumerate(urls[:5], 1):
                logger.info(f"      {i}. {url}")
            if len(urls) > 5:
                logger.info(f"      ... and {len(urls) - 5} more")
    except Exception as e:
        logger.error(f"❌ Failed to discover URLs: {e}")
        sys.exit(1)

    # ── Step 2: Scrape pages ──────────────────────────────────────────────
    logger.info("\n📄 Step 2: Scraping pages...")

    try:
        pages = scraper.scrape_all()
        logger.info(f"   ✅ Successfully scraped {len(pages)} valid pages")

        if not pages:
            logger.warning("   ⚠️  No valid pages were scraped. Check URL accessibility.")
            sys.exit(1)

        logger.info("\n   Scraped pages summary:")
        for page in pages[:3]:
            title = page.get("title", "Unknown")
            url = page.get("url", "Unknown")
            content_len = len(page.get("content", ""))
            logger.info(f"      • {title} ({content_len:,} chars)")
        if len(pages) > 3:
            logger.info(f"      ... and {len(pages) - 3} more")

    except Exception as e:
        logger.error(f"❌ Failed to scrape pages: {e}")
        sys.exit(1)

    # ── Step 3: Index in Supabase ────────────────────────────────────────
    logger.info("\n🗂️  Step 3: Processing and indexing in Supabase...")

    try:
        embedding_manager = EmbeddingManager()
        added = embedding_manager.process_and_index(pages)
        logger.info(f"   ✅ Successfully indexed {added} document chunks")

        logger.info("\n   Storage estimate:")
        logger.info(f"      • URLs scraped: {len(pages)}")
        logger.info(f"      • Chunks indexed: {added}")
        logger.info(f"      • Estimated size: ~{added * 0.1:.1f} MB (very safe for free tier)")

    except Exception as e:
        logger.error(f"❌ Failed to index documents: {e}")
        logger.error(f"   Check your Supabase credentials and connection")
        sys.exit(1)

    # ── Success Summary ───────────────────────────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("✅ SCRAPING AND INDEXING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\nSummary:")
    logger.info(f"  • URLs discovered: {len(urls)}")
    logger.info(f"  • Pages scraped: {len(pages)}")
    logger.info(f"  • Chunks indexed: {added}")
    logger.info(f"\nNext steps:")
    logger.info(f"  1. Start backend:  uvicorn src.main:app --reload")
    logger.info(f"  2. Start frontend: cd frontend && npm run dev")
    logger.info(f"  3. Visit: http://localhost:3000")
    logger.info(f"  4. Ask questions about BBVA products!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    main()
