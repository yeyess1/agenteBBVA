"""
Web scraper module
Extracts content from bank website and prepares for vectorization
"""

import logging
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

from src.config import settings

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Scrapes content from bank website
    """

    def __init__(self, base_url: str = None):
        """
        Initialize scraper
        Args:
            base_url: Bank website URL (defaults to settings.bank_website_url)
        """
        self.base_url = base_url or settings.bank_website_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch page content with robust error handling
        Args:
            url: URL to fetch
        Returns:
            Page HTML content or None if failed
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Try to decode with detected encoding, fallback to utf-8
            try:
                return response.text
            except (UnicodeDecodeError, AttributeError):
                return response.content.decode('utf-8', errors='ignore')

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_text(self, html: str) -> str:
        """
        Extract clean text from HTML
        Args:
            html: HTML content
        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text

    def scrape_url(self, url: str) -> Optional[Dict]:
        """
        Scrape single URL and extract content
        Args:
            url: URL to scrape
        Returns:
            Dict with url, title, and content (HTML for hybrid chunking), or None if failed
        """
        logger.info(f"Scraping {url}")
        html = self.fetch_page(url)
        if not html or not html.strip():
            logger.warning(f"No content from {url}")
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string if soup.title else "Unknown"

            # Validate that we got actual HTML content
            if not soup.body and not soup.find("main") and not soup.find("article"):
                logger.warning(f"No valid HTML structure in {url}")
                return None

            return {
                "url": url,
                "title": title,
                "content": html,
            }
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None

    def get_sitemap_urls(self) -> List[str]:
        """
        Get URLs from sitemap + fallback product URLs for comprehensive coverage
        Returns:
            List of URLs from sitemap + additional product pages
        """
        sitemap_url = settings.bank_website_sitemap_url or f"{self.base_url.rstrip('/')}/sitemap.xml"
        logger.info(f"Fetching sitemap from {sitemap_url}")

        urls = []
        html = self.fetch_page(sitemap_url)
        if html:
            soup = BeautifulSoup(html, "xml")
            for loc in soup.find_all("loc"):
                url = loc.text.strip()
                base_clean = self.base_url.rstrip("/")
                if url.startswith(base_clean):
                    urls.append(url)
            logger.info(f"Found {len(urls)} URLs in sitemap")
        else:
            logger.warning("Failed to fetch sitemap")

        # Fallback: Add essential product URLs if sitemap is incomplete
        base_clean = self.base_url.rstrip("/")
        if len(urls) < 20:
            logger.info("Sitemap incomplete, adding essential product URLs...")
            product_urls = [
                f"{base_clean}/personas/productos/cuentas/",
                f"{base_clean}/personas/productos/tarjetas/",
                f"{base_clean}/personas/productos/depositos-e-inversion/",
                f"{base_clean}/personas/productos/creditos/",
                f"{base_clean}/personas/productos/prestamos/",
                f"{base_clean}/personas/productos/seguros/",
                f"{base_clean}/empresas/productos/",
                f"{base_clean}/pymes/productos/",
            ]

            # Add URLs that aren't already in sitemap
            for url in product_urls:
                if url not in urls:
                    urls.append(url)

            logger.info(f"Added {len(product_urls)} product URLs, total now: {len(urls)}")

        return urls if urls else [self.base_url]

    def scrape_all(self) -> List[Dict]:
        """
        Scrape all content from bank website
        Returns:
            List of scraped pages with content
        """
        urls = self.get_sitemap_urls()
        logger.info(f"Found {len(urls)} URLs to scrape")

        pages = []
        for i, url in enumerate(urls, 1):
            logger.info(f"Scraping {i}/{len(urls)}: {url}")
            result = self.scrape_url(url)
            if result:
                pages.append(result)

        logger.info(f"Successfully scraped {len(pages)}/{len(urls)} pages")
        return pages
