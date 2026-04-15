"""
Conversation memory module
Manages conversation history per user via Supabase
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from supabase import create_client

from src.config import settings

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history per user ID using Supabase
    Stores messages array as JSONB per user
    """

    def __init__(self, storage_dir: str = None):
        """
        Initialize conversation memory with Supabase backend
        Args:
            storage_dir: Deprecated, kept for backward compatibility
        """
        self.client = create_client(
            settings.supabase_url,
            settings.supabase_api_key
        )
        logger.info("Initialized Supabase conversation memory")

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
    ) -> Dict:
        """
        Add message to conversation
        Args:
            user_id: Unique user identifier
            role: 'user' or 'assistant'
            content: Message content
        Returns:
            Added message object with timestamp
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            new_message = {
                "role": role,
                "content": content,
                "timestamp": timestamp,
            }

            # Get existing conversation
            conversation = self._load_conversation(user_id)
            messages = conversation.get("messages", [])

            # Add new message
            messages.append(new_message)

            # Enforce max_conversation_length
            if len(messages) > settings.max_conversation_length:
                messages = messages[-settings.max_conversation_length:]

            # Update or insert conversation
            self._save_conversation(user_id, messages)

            logger.info(f"Added {role} message to conversation {user_id}")
            return new_message

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    def get_messages(
        self,
        user_id: str,
        last_n: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get last N messages from conversation
        Args:
            user_id: User identifier
            last_n: Get last N messages (defaults to CONTEXT_WINDOW)
        Returns:
            List of messages in chronological order
        """
        last_n = last_n or settings.context_window

        try:
            conversation = self._load_conversation(user_id)
            messages = conversation.get("messages", [])

            if last_n and len(messages) > last_n:
                messages = messages[-last_n:]

            logger.info(f"Retrieved {len(messages)} messages for user {user_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []

    def get_full_history(self, user_id: str) -> List[Dict]:
        """
        Get full conversation history for user
        Args:
            user_id: User identifier
        Returns:
            Full list of all messages in chronological order
        """
        try:
            conversation = self._load_conversation(user_id)
            messages = conversation.get("messages", [])

            logger.info(f"Retrieved full history: {len(messages)} messages for user {user_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving full history: {e}")
            return []

    def clear_conversation(self, user_id: str) -> bool:
        """
        Clear all conversation messages for user
        Args:
            user_id: User identifier
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the conversation row
            self.client.table("conversations").delete().eq(
                "user_id", user_id
            ).execute()

            logger.info(f"Cleared conversation for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            return False

    def _load_conversation(self, user_id: str) -> Dict:
        """
        Load conversation from Supabase
        Args:
            user_id: User identifier
        Returns:
            Conversation dict with messages array
        """
        try:
            result = self.client.table("conversations").select(
                "*"
            ).eq("user_id", user_id).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            # Return empty conversation structure
            return {
                "user_id": user_id,
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return {
                "user_id": user_id,
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
            }

    def _save_conversation(self, user_id: str, messages: List[Dict]) -> bool:
        """
        Save conversation to Supabase (insert or update)
        Args:
            user_id: User identifier
            messages: Array of messages
        Returns:
            True if successful
        """
        try:
            # Check if conversation exists
            existing = self.client.table("conversations").select(
                "id"
            ).eq("user_id", user_id).execute()

            if existing.data and len(existing.data) > 0:
                # Update existing
                self.client.table("conversations").update({
                    "messages": messages,
                    "updated_at": datetime.utcnow().isoformat(),
                }).eq("user_id", user_id).execute()
            else:
                # Insert new
                self.client.table("conversations").insert({
                    "user_id": user_id,
                    "messages": messages,
                }).execute()

            return True

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
