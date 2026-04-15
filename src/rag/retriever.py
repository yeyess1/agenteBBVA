"""
Document retriever module
Retrieves and reranks relevant documents from vector store using advanced RAG techniques
"""

import logging
import unicodedata
import re
from typing import List, Dict, Optional
import numpy as np

from src.vectorizer.embedding import EmbeddingManager
from src.config import settings

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """
    Advanced document retriever with score threshold filtering, MMR reranking,
    and relevance-aware context formatting
    """

    # BBVA Colombia banking synonyms for query expansion
    BANKING_SYNONYMS = {
        "cdt": "certificado de depósito a término",
        "cdts": "certificados de depósito a término",
        "pse": "pagos seguros en línea",
        "nit": "número de identificación tributaria",
        "cc": "cédula de ciudadanía",
        "ta": "tarjeta de ahorro",
        "tc": "tarjeta de crédito",
        "tdc": "tarjeta de crédito débito",
        "tdd": "tarjeta de débito",
        "cupo": "límite de crédito",
        "mipyme": "micro pequeña mediana empresa",
        "aqua": "cuenta de ahorro Aqua",
        "bbva net": "banca digital BBVA Net",
        "bbva wallet": "billetera BBVA Wallet",
        "aval": "Grupo Aval",
    }

    # BGE-M3 score bands for cosine similarity
    SCORE_BANDS = {
        "high": (0.75, 1.0),     # Paraphrase or exact match
        "medium": (0.55, 0.74),  # Topic match, different phrasing
        "low": (0.40, 0.54),     # Related domain, possibly useful
    }

    def __init__(self):
        """Initialize retriever with embedding manager"""
        self.embedding_manager = EmbeddingManager()

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve and rerank documents relevant to query
        Pipeline:
          1. Preprocess query (unicode normalization, whitespace)
          2. Expand with banking synonyms
          3. Over-fetch candidates for MMR
          4. Apply score threshold filtering
          5. Apply MMR reranking
        Args:
            query: User query
            top_k: Number of documents to return
        Returns:
            List of retrieved and reranked documents
        """
        top_k = top_k or settings.retrieval_top_k
        logger.info(f"Retrieving documents for query: {query[:50]}...")

        # Step 1: Query preprocessing
        query_processed = self._preprocess_query(query)
        query_expanded = self._expand_query(query_processed)

        # Step 2: Over-fetch candidates for MMR (2x top_k or minimum 10)
        candidate_k = max(top_k * 2, 10)
        logger.debug(f"Over-fetching {candidate_k} candidates for MMR pool")
        results = self.embedding_manager.search_similar(query_expanded, n_results=candidate_k)

        if not results:
            logger.warning("No documents retrieved from vector store")
            return []

        # Step 3: Apply score threshold filtering
        results = self._apply_threshold(results, top_k)
        if not results:
            return []

        # Step 4: Apply MMR reranking (if we have more than top_k)
        if len(results) > top_k:
            results = self._mmr_rerank(query_expanded, results, top_k)

        logger.info(f"Retrieved and reranked {len(results)} documents (threshold: {settings.retrieval_score_threshold})")
        return results

    def _preprocess_query(self, query: str) -> str:
        """
        Normalize query: unicode NFC, collapse whitespace
        Args:
            query: Raw query text
        Returns:
            Normalized query
        """
        # Normalize unicode (e.g., é composed vs decomposed)
        query = unicodedata.normalize("NFC", query)
        # Collapse multiple whitespace
        query = re.sub(r"\s+", " ", query).strip()
        return query

    def _expand_query(self, query: str) -> str:
        """
        Expand query with banking domain synonyms
        If query contains known abbreviations, append their expansions
        Args:
            query: Preprocessed query
        Returns:
            Query with synonym expansions appended
        """
        lower = query.lower()
        expansions = []

        for abbr, expansion in self.BANKING_SYNONYMS.items():
            if f" {abbr} " in f" {lower} " or lower.startswith(abbr + " ") or lower.endswith(f" {abbr}"):
                expansions.append(expansion)

        if expansions:
            expanded = f"{query} {' '.join(expansions)}"
            logger.debug(f"Query expanded with {len(expansions)} synonyms")
            return expanded

        return query

    def _apply_threshold(self, results: List[Dict], top_k: int) -> List[Dict]:
        """
        Filter results by score threshold; fallback if none pass
        Args:
            results: Retrieved documents with distance scores
            top_k: Target number of results
        Returns:
            Filtered results (with fallback to top-1 if none pass threshold)
        """
        threshold = settings.retrieval_score_threshold
        above_threshold = [d for d in results if d.get("distance", 0) >= threshold]

        if above_threshold:
            logger.info(f"Filtered to {len(above_threshold)} docs above threshold {threshold:.2f}")
            return above_threshold

        # Graceful fallback: return best doc even if below threshold
        # This prevents hallucination from empty retrieval context
        if results:
            best_score = results[0].get("distance", 0)
            logger.warning(
                f"No documents above threshold {threshold:.2f}. "
                f"Best available score: {best_score:.3f}. "
                "Returning top-1 as fallback."
            )
            return results[:1]

        return []

    def _mmr_rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int,
    ) -> List[Dict]:
        """
        Maximal Marginal Relevance reranking to balance relevance and diversity
        Formula: MMR(d) = λ·sim(d, query) - (1-λ)·max_sim(d, already_selected)

        This re-encodes documents on CPU (~500-1500ms for 10 docs depending on hardware)
        but provides superior diversity while maintaining relevance.

        Args:
            query: User query
            documents: Retrieved documents
            top_k: Number of top results to select

        Returns:
            Reranked documents
        """
        if len(documents) <= top_k:
            return documents

        logger.info(f"Applying MMR reranking (λ={settings.mmr_lambda}) with {len(documents)} candidates")

        # Re-encode query and documents to obtain in-memory vectors
        model = self.embedding_manager.vector_store.model
        doc_texts = [d["content"] for d in documents]

        logger.debug(f"Re-encoding query and {len(documents)} documents for MMR...")
        doc_embeddings = model.encode(
            doc_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        # Compute cosine similarity helper
        def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
            """Compute cosine similarity between two vectors"""
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b + 1e-10))

        # Precompute query similarities
        query_sims = np.array([cosine_sim(doc_embeddings[i], query_embedding) for i in range(len(documents))])

        # Iterative MMR selection
        selected_indices: List[int] = []
        candidate_indices = list(range(len(documents)))
        lambda_param = settings.mmr_lambda

        while len(selected_indices) < top_k and candidate_indices:
            if not selected_indices:
                # First selection: highest query similarity
                best_idx = max(candidate_indices, key=lambda i: query_sims[i])
            else:
                # MMR score: balance relevance vs diversity
                def mmr_score(candidate_idx: int) -> float:
                    relevance = query_sims[candidate_idx]
                    # Maximum similarity to already selected documents
                    max_similarity_to_selected = max(
                        cosine_sim(doc_embeddings[candidate_idx], doc_embeddings[selected_idx])
                        for selected_idx in selected_indices
                    )
                    return lambda_param * relevance - (1 - lambda_param) * max_similarity_to_selected

                best_idx = max(candidate_indices, key=mmr_score)

            selected_indices.append(best_idx)
            candidate_indices.remove(best_idx)

        reranked = [documents[i] for i in selected_indices]
        logger.info(f"MMR reranking complete: selected {len(reranked)} diverse documents")
        return reranked

    def format_context(self, documents: List[Dict]) -> str:
        """
        Format retrieved documents for LLM context with relevance scores
        Includes numeric scores and qualitative labels to calibrate model confidence
        Args:
            documents: List of retrieved documents
        Returns:
            Formatted context string
        """
        if not documents:
            return "No se encontraron documentos relevantes."

        parts = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            url = metadata.get("url", "fuente desconocida")
            title = metadata.get("title", "")
            score = doc.get("distance", 0.0)
            label = self._score_label(score)
            content = doc.get("content", "")

            header = f"[Fuente {i}: {title} | {url} | Relevancia: {score:.2f} ({label})]"
            parts.append(f"{header}\n{content}\n")

        return "\n---\n".join(parts)

    def _score_label(self, score: float) -> str:
        """
        Convert numeric similarity score to qualitative label
        Args:
            score: Cosine similarity score (0-1)
        Returns:
            Spanish label: "Alta relevancia", "Relevancia media", or "Baja relevancia"
        """
        if score >= 0.75:
            return "Alta relevancia"
        if score >= 0.55:
            return "Relevancia media"
        return "Baja relevancia"

    def assess_context_quality(self, documents: List[Dict]) -> str:
        """
        Assess overall quality of retrieved context based on top document score
        Used by generator to adjust response hedging (confidence/uncertainty)
        Args:
            documents: Retrieved documents
        Returns:
            Quality level: "high", "medium", "low", or "none"
        """
        if not documents:
            return "none"

        top_score = documents[0].get("distance", 0.0)

        if top_score >= 0.70:
            return "high"
        if top_score >= 0.50:
            return "medium"
        return "low"

    def get_sources(self, documents: List[Dict]) -> List[Dict]:
        """
        Extract unique source information from documents for citation
        Args:
            documents: List of retrieved documents
        Returns:
            List of unique sources with url and title
        """
        sources = {}
        for doc in documents:
            metadata = doc.get("metadata", {})
            url = metadata.get("url")
            title = metadata.get("title")

            if url and url not in sources:
                sources[url] = {"url": url, "title": title}

        return list(sources.values())
