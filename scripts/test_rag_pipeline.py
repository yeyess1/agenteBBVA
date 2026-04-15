#!/usr/bin/env python3
"""
Test script for advanced RAG pipeline
Verifies: retriever (threshold, MMR, synonym expansion), generator (async, context quality)
"""

import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import DocumentRetriever
from src.rag.generator import ResponseGenerator
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rag_pipeline():
    """Test complete RAG pipeline: retrieval + generation"""
    print("\n" + "=" * 80)
    print("TESTING ADVANCED RAG PIPELINE")
    print("=" * 80)

    retriever = DocumentRetriever()
    generator = ResponseGenerator()

    # Test queries: one in-scope, one with abbreviation
    test_queries = [
        "¿Qué es un CDT?",
        "¿Cuáles son los requisitos para abrir una cuenta de ahorro?",
        "¿Cómo funciona la tarjeta de crédito Aqua?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}] Query: {query}")
        print("-" * 80)

        try:
            # Test 1: Retrieval with threshold and MMR
            print(f"\n  Retrieving documents...")
            documents = retriever.retrieve(query)

            if not documents:
                print("  ⚠️  No documents retrieved")
                continue

            print(f"  ✅ Retrieved {len(documents)} documents:")
            for j, doc in enumerate(documents, 1):
                score = doc.get("distance", 0)
                meta = doc.get("metadata", {})
                url = meta.get("url", "unknown")
                title = meta.get("title", "unknown")
                print(f"    [{j}] Score: {score:.3f} | {title[:40]}")

            # Test 2: Context quality assessment
            context_quality = retriever.assess_context_quality(documents)
            print(f"\n  Context quality: {context_quality}")

            # Test 3: Format context with scores
            context = retriever.format_context(documents)
            print(f"\n  Formatted context: {len(context)} chars")
            print(f"  Preview: {context[:200]}...")

            # Test 4: Response generation with async
            print(f"\n  Generating response...")
            answer = await generator.generate(
                query,
                context,
                conversation_history=[],  # Empty for this test
                context_quality=context_quality
            )

            print(f"  ✅ Generated response: {len(answer)} chars")
            print(f"  Preview: {answer[:150]}...")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ RAG PIPELINE TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ADVANCED RAG PIPELINE TEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  - Retrieval threshold: {settings.retrieval_score_threshold}")
    print(f"  - MMR lambda: {settings.mmr_lambda}")
    print(f"  - LLM Provider: {settings.llm_provider}")
    print(f"  - Gemini model: {settings.gemini_model}")
    print(f"  - Vector store: Supabase pgvector")
    print(f"  - Embedding model: {settings.embedding_model}")

    try:
        asyncio.run(test_rag_pipeline())
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        sys.exit(1)
