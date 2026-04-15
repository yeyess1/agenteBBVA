"""
Response generator module
Generates responses using Google Gemini API with advanced RAG prompt engineering
"""

import logging
from typing import List, Dict, Optional
import asyncio
import google.generativeai as genai

from src.config import settings

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Advanced response generator using Google Gemini with RAG-specific
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
        """Initialize response generator with Gemini API"""
        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. Set it in .env file."
            )
        genai.configure(api_key=api_key)
        self.model = settings.gemini_model
        logger.info(f"Initialized Gemini generator with model: {self.model}")

    async def generate(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
        context_quality: str = "medium",
    ) -> str:
        """
        Generate response using Google Gemini API with RAG context and conversation history
        Args:
            query: User's current question
            context: Retrieved relevant documents with scores
            conversation_history: Previous messages in conversation (clean, no context blobs)
            context_quality: Quality signal: "high", "medium", "low", or "none"
        Returns:
            Generated response text
        """
        logger.info(f"Generating response with Gemini (context_quality={context_quality})")

        try:
            # Build messages with proper RAG architecture
            formatted_messages = self._build_messages(query, context, conversation_history, context_quality)

            # Run Gemini API call in thread pool to avoid blocking event loop
            response_text = await asyncio.to_thread(
                self._call_gemini_sync,
                formatted_messages
            )

            logger.info(f"Generated response ({len(response_text)} characters)")
            return response_text

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def _call_gemini_sync(self, formatted_messages: List[Dict]) -> str:
        """
        Synchronous Gemini API call (executed in thread pool)

        Args:
            formatted_messages: List of dicts with 'role' and 'content' keys

        Returns:
            Generated response text
        """
        # Initialize model with system prompt
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self.SYSTEM_PROMPT,
            generation_config={
                "max_output_tokens": 2048,
                "temperature": 0.7,
            }
        )

        # Prepare conversation content
        # For first message, prepend RAG context; for history, use clean exchanges
        contents = []

        # Add conversation history (clean exchanges without context)
        for msg in formatted_messages[:-1]:  # All except last message
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [msg["content"]]})

        # Add current message with RAG context (last message)
        last_msg = formatted_messages[-1]
        contents.append({"role": "user", "parts": [last_msg["content"]]})

        # Generate response
        response = model.generate_content(contents)

        # Extract text from response
        if response.text:
            return response.text

        raise ValueError(f"Empty response from Gemini API")

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
        context_quality: str,
    ) -> List[Dict]:
        """
        Build message list for Gemini API with proper RAG architecture

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
            # Convert role: "assistant" becomes "model" in Gemini API
            role = "model" if msg["role"] == "assistant" else "user"
            messages.append({
                "role": role,
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
