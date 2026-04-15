"""
Response generator module
Generates responses using Claude API with advanced RAG prompt engineering
"""

import logging
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic

from src.config import settings

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Advanced response generator using AsyncAnthropic with RAG-specific
    prompt engineering, context quality signals, and confidence/uncertainty handling
    """

    # Expert RAG system prompt with 5 sections:
    # 1. Role definition
    # 2. Citation rules
    # 3. Uncertainty handling
    # 4. Tone and format
    # 5. Scope limitations
    SYSTEM_PROMPT = """Eres un asistente especializado en servicios financieros del banco BBVA Colombia.
Tu función es responder preguntas de clientes basándote exclusivamente en el contexto documental proporcionado en cada consulta.

## REGLAS DE CITACIÓN
- Cuando respondas, indica siempre la fuente de cada afirmación usando el número de fuente del contexto.
- Por ejemplo: "Según la Fuente 1, el requisito es..."
- Si múltiples fuentes confirman un dato, menciona ambas: "Las Fuentes 1 y 3 indican que..."
- Usa las puntuaciones de relevancia proporcionadas para evaluar qué tan confiable es cada fuente.
- No inventes información que no esté en el contexto. Prioriza fuentes con alta relevancia (>0.75).

## MANEJO DE INCERTIDUMBRE
- Si el contexto es insuficiente o de baja relevancia, responde explícitamente:
  "Basándome en la información disponible, no tengo datos suficientes para responder con certeza. Te recomiendo contactar al centro de atención al cliente al 0-1-BBVA (0-1-2282) o visita bbva.com.co"
- Si la pregunta es ambigua o podría interpretarse de múltiples formas, solicita clarificación antes de responder.
- Si el contexto parece contradecir información de turnos anteriores en la conversación, señálalo explícitamente.
- Usa frases de hedging cuando sea apropiado: "según los documentos disponibles", "basándome en la información proporcionada".

## TONO Y FORMATO
- Responde siempre en español colombiano, con tuteo formal (usted).
- Sé conciso pero completo. Evita redundancias.
- Para procedimientos o pasos: presenta como lista numerada.
- Para requisitos o documentación: presenta como lista con viñetas.
- Para comparaciones: usa tablas cuando sea relevante.
- Nunca uses lenguaje coloquial excesivo, emoticones, o diminutivos innecesarios.

## LIMITACIONES DE SCOPE
- Solo respondes sobre productos, servicios y políticas del BBVA Colombia.
- No ofreces asesoría legal, tributaria, de inversiones o de seguros.
  Para estos temas, responde: "Este tema requiere asesoría especializada. Te recomendamos contactar a un asesor de BBVA."
- Para transacciones específicas de cuenta (saldos, movimientos, historial):
  Indica que el cliente debe usar los canales seguros del banco (BBVA Net, app móvil, o sucursal).
- Si la pregunta es completamente fuera de dominio (no sobre BBVA): responde amablemente indicando que solo asistes con temas del banco."""

    def __init__(self):
        """Initialize response generator with AsyncAnthropic client"""
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
        context_quality: str = "medium",
    ) -> str:
        """
        Generate response using Claude API with RAG context and conversation history
        Args:
            query: User's current question
            context: Retrieved relevant documents with scores
            conversation_history: Previous messages in conversation (clean, no context blobs)
            context_quality: Quality signal: "high", "medium", "low", or "none"
        Returns:
            Generated response text
        """
        logger.info(f"Generating response (context_quality={context_quality})")

        # Build message list with proper RAG architecture
        messages = self._build_messages(query, context, conversation_history, context_quality)

        try:
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": self.SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},  # Enable prompt caching
                    }
                ],
                messages=messages,
            )

            assistant_response = response.content[0].text

            # Log prompt caching metrics if available
            if hasattr(response, "usage"):
                cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
                cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0)
                if cache_read > 0 or cache_creation > 0:
                    logger.info(
                        f"Prompt caching: read={cache_read} tokens, "
                        f"creation={cache_creation} tokens"
                    )

            logger.info(f"Generated response ({len(assistant_response)} characters)")
            return assistant_response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
        context_quality: str,
    ) -> List[Dict]:
        """
        Build message list for Claude API with proper RAG architecture

        Key RAG pattern:
        - Conversation history: clean exchanges (no context blobs)
          This preserves dialog flow and makes history interpretable.
        - Current user message: context injected as structured prefix
          This grounds the question in freshly-retrieved documents.

        This is the correct RAG message architecture, avoiding the anti-pattern
        of contaminating historical turns with context data.

        Args:
            query: User's question
            context: Retrieved documents (already formatted with scores)
            conversation_history: Previous message dicts with role/content
            context_quality: "high", "medium", "low", or "none"

        Returns:
            Messages list for API
        """
        messages = []

        # Step 1: Add clean conversation history (no context contamination)
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],  # bare message text only
            })

        # Step 2: Map context quality to instruction note
        quality_notes = {
            "high": "Los documentos recuperados tienen alta relevancia (score > 0.70) para esta pregunta. Responde con confianza basándote en ellos.",
            "medium": "Los documentos recuperados tienen relevancia moderada (score 0.50-0.70). Responde usando estos documentos pero con cuidado.",
            "low": "Los documentos recuperados tienen baja relevancia (score < 0.50). Indica claramente si no tienes información suficiente.",
            "none": "No se encontraron documentos relevantes. Indica que no tienes información disponible para responder.",
        }
        quality_note = quality_notes.get(context_quality, "")

        # Step 3: Build current user message with RAG context
        # Structure: quality signal → documents → question
        current_user_content = (
            f"## Calidad del contexto recuperado\n\n{quality_note}\n\n"
            f"## Documentos de referencia\n\n{context}\n\n"
            f"---\n\n"
            f"## Pregunta del cliente\n\n{query}"
        )

        messages.append({
            "role": "user",
            "content": current_user_content,
        })

        return messages
