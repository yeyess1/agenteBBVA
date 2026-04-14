"""
Response generator module
Generates responses using Claude API with retrieved context
"""

import logging
from typing import List, Dict, Optional
from anthropic import Anthropic

from src.config import settings

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates responses using Claude API
    """

    SYSTEM_PROMPT = """You are a helpful assistant for a Colombian bank's customer support.
Your role is to answer questions about the bank's services, products, and policies based on the provided context.

Guidelines:
- Answer questions accurately based on the provided context
- If the information is not in the context, say so clearly
- Always be polite and professional
- Provide specific information when available
- For contact information, always mention that customers can call the bank's support line for more details
- Respond in Spanish (en español) since this is for a Colombian bank"""

    def __init__(self):
        """Initialize response generator with Claude API"""
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    def generate(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
    ) -> str:
        """
        Generate response using Claude API
        Args:
            query: User's current question
            context: Retrieved relevant documents
            conversation_history: Previous messages in conversation
        Returns:
            Generated response
        """
        logger.info(f"Generating response for query: {query[:50]}...")

        # Build messages for API
        messages = self._build_messages(query, context, conversation_history)

        try:
            response = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=messages,
            )

            assistant_response = response.content[0].text
            logger.info(f"Generated response ({len(assistant_response)} chars)")
            return assistant_response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict],
    ) -> List[Dict]:
        """
        Build message list for Claude API
        Args:
            query: Current question
            context: Retrieved context
            conversation_history: Conversation history
        Returns:
            Formatted messages for API
        """
        messages = []

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add current query with context
        context_prompt = f"""Based on the following information from the bank's website, please answer the question:

CONTEXT:
{context}

QUESTION:
{query}

Please provide a helpful and accurate answer based on the context above."""

        messages.append({
            "role": "user",
            "content": context_prompt,
        })

        return messages
