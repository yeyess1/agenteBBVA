"""
Conversation memory module
Manages conversation history per user
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history per user ID
    Supports both in-memory and persistent storage
    """

    def __init__(self, storage_dir: str = ".conversations"):
        """
        Initialize conversation memory
        Args:
            storage_dir: Directory for storing conversation files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        # In-memory cache for active conversations
        self._cache = {}

    def _get_conversation_file(self, user_id: str) -> Path:
        """Get path for user's conversation file"""
        return self.storage_dir / f"{user_id}.json"

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
            Added message object
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Load existing conversation
        conversation = self._load_conversation(user_id)
        conversation["messages"].append(message)

        # Enforce max length
        if len(conversation["messages"]) > settings.max_conversation_length:
            conversation["messages"] = conversation["messages"][
                -settings.max_conversation_length:
            ]

        # Save conversation
        self._save_conversation(user_id, conversation)

        logger.info(f"Added {role} message to conversation {user_id}")
        return message

    def get_messages(
        self,
        user_id: str,
        last_n: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get conversation messages
        Args:
            user_id: User identifier
            last_n: Get last N messages (defaults to CONTEXT_WINDOW)
        Returns:
            List of messages
        """
        last_n = last_n or settings.context_window
        conversation = self._load_conversation(user_id)
        messages = conversation["messages"]

        if last_n and len(messages) > last_n:
            return messages[-last_n:]
        return messages

    def get_full_history(self, user_id: str) -> List[Dict]:
        """
        Get full conversation history for user
        Args:
            user_id: User identifier
        Returns:
            Full list of all messages
        """
        conversation = self._load_conversation(user_id)
        return conversation["messages"]

    def clear_conversation(self, user_id: str) -> bool:
        """
        Clear conversation for user
        Args:
            user_id: User identifier
        Returns:
            True if successful
        """
        try:
            file_path = self._get_conversation_file(user_id)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleared conversation for user {user_id}")

            # Clear cache
            if user_id in self._cache:
                del self._cache[user_id]

            return True
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            return False

    def _load_conversation(self, user_id: str) -> Dict:
        """Load conversation from storage or cache"""
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]

        # Try to load from file
        file_path = self._get_conversation_file(user_id)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    conversation = json.load(f)
                    self._cache[user_id] = conversation
                    return conversation
            except Exception as e:
                logger.error(f"Error loading conversation: {e}")

        # Create new conversation
        conversation = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }
        self._cache[user_id] = conversation
        return conversation

    def _save_conversation(self, user_id: str, conversation: Dict) -> bool:
        """Save conversation to file"""
        try:
            file_path = self._get_conversation_file(user_id)
            with open(file_path, "w") as f:
                json.dump(conversation, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
