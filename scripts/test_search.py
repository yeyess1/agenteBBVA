#!/usr/bin/env python3
"""
Test script para búsqueda vectorial en Chroma DB
Uso: python scripts/test_search.py "tu pregunta aquí"

Ejemplo:
  python scripts/test_search.py "¿Cuáles son los productos de inversión?"
  python scripts/test_search.py "¿Cómo solicitar un crédito?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import DocumentRetriever


def search(query: str):
    """Test semantic search"""
    print(f"\n🔍 Buscando: {query}\n")
    print("=" * 80)

    retriever = DocumentRetriever()
    results = retriever.retrieve(query, top_k=5)

    if not results:
        print("No results found")
        return

    for i, doc in enumerate(results, 1):
        print(f"\n[Resultado {i}]")
        print(f"  Relevancia: {1 - doc.get('distance', 0):.2%}")
        print(f"  Fuente: {doc['metadata'].get('url', 'Unknown')}")
        print(f"  Título: {doc['metadata'].get('title', 'Unknown')}")
        print(f"\n  Contenido:")
        content = doc['content'][:300]
        print(f"  {content}...")

    print("\n" + "=" * 80)
    print(f"✅ Found {len(results)} relevant documents\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_search.py \"tu pregunta aquí\"")
        print("\nEjemplos:")
        print('  python scripts/test_search.py "¿Cuáles son los productos de inversión?"')
        print('  python scripts/test_search.py "¿Cómo solicitar un crédito?"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    search(query)
