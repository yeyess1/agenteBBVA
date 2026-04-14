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
        Fetch page content
        Args:
            url: URL to fetch
        Returns:
            Page HTML content or None if failed
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
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
            Dict with url, title, and content, or None if failed
        """
        logger.info(f"Scraping {url}")
        html = self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "Unknown"
        content = self.extract_text(html)

        if not content.strip():
            logger.warning(f"No content extracted from {url}")
            return None

        return {
            "url": url,
            "title": title,
            "content": content,
        }

    def get_sitemap_urls(self) -> List[str]:
        """
        Get URLs from sitemap
        Returns:
            List of URLs from sitemap
        """
        sitemap_url = settings.bank_website_sitemap_url or f"{self.base_url}/sitemap.xml"
        logger.info(f"Fetching sitemap from {sitemap_url}")

        html = self.fetch_page(sitemap_url)
        if not html:
            logger.warning("Failed to fetch sitemap, will scrape homepage only")
            return [self.base_url]

        soup = BeautifulSoup(html, "xml")
        urls = []

        for loc in soup.find_all("loc"):
            url = loc.text
            if url.startswith(self.base_url.rstrip("/")):
                urls.append(url)

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
