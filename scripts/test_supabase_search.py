#!/usr/bin/env python3
"""
Test script para verificar indexación y búsqueda en Supabase + pgvector
Usa el scraper y chunker existente, luego indexa y busca en Supabase
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.web_scraper import WebScraper
from src.vectorizer.embedding import EmbeddingManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_supabase_indexing_and_search():
    """Test Supabase indexing and semantic search with BGE-M3"""
    print("\n" + "=" * 80)
    print("TESTING SUPABASE INDEXING & SEARCH")
    print("=" * 80)

    # Scrape página de BBVA
    print("\n[1] Scraping BBVA...")
    scraper = WebScraper()
    url = "https://www.bbva.com.co/personas/productos/prestamos/vivienda/hipotecario.html"

    logger.info(f"Fetching: {url}")
    html = scraper.fetch_page(url)
    if not html:
        print("❌ Failed to fetch page")
        return False

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string if soup.title else "Unknown"

    page_data = {
        "url": url,
        "title": title,
        "content": html,
    }

    print(f"✅ Scraped: {title}")

    # Indexar en Supabase
    print("\n[2] Indexing in Supabase with BGE-M3 embeddings...")
    embedding_manager = EmbeddingManager()
    indexed_count = embedding_manager.process_and_index([page_data])
    print(f"✅ Indexed {indexed_count} chunks")

    # Mostrar stats
    print("\n[3] Vector Store Statistics:")
    stats = embedding_manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Test búsquedas
    print("\n[4] Testing semantic search queries:")
    print("-" * 80)

    test_queries = [
        "¿Cuál es la tasa de interés del crédito hipotecario?",
        "¿Cuáles son los requisitos para solicitar un préstamo?",
        "¿Qué documentos necesito?",
        "Información sobre financiamiento de vivienda",
        "Plazos y tasas de hipotecas",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[Query {i}] {query}")
        results = embedding_manager.search_similar(query)

        if results:
            print(f"✅ Found {len(results)} results:")
            for j, result in enumerate(results[:3], 1):
                content = result['content'][:150].replace('\n', ' ')
                similarity = result.get('distance', 0)
                source = result['metadata'].get('url', 'Unknown')
                print(f"\n   [{j}] Similarity: {similarity:.4f}")
                print(f"       Source: {source}")
                print(f"       Content: {content}...")
        else:
            print(f"⚠️  No results found")

    print("\n" + "=" * 80)
    print("✅ SUPABASE INDEXING & SEARCH TEST COMPLETE!")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = test_supabase_indexing_and_search()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
