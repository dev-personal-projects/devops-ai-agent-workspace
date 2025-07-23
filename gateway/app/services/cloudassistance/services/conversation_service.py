from typing import Optional, Dict, Any, List
import uuid
import logging
from  gateway.app.services.cloudassistance.models.chat_models import  ChatMessage

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Manages conversation state and context.
    Implements Single Responsibility Principle - only handles conversation logic.
    """

    def __init__(self):
        # In-memory storage for demo purposes
        # In production, use Redis or database
        self._conversations: Dict[str, List[ChatMessage]] = {}

    def create_conversation_id(self) -> str:
        """Generate a new conversation ID"""
        return str(uuid.uuid4())

    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        """Add a message to conversation history"""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        self._conversations[conversation_id].append(message)
        logger.info(f"Added message to conversation {conversation_id}")

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[ChatMessage]:
        """
        Get recent conversation history.

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of recent messages to return

        Returns:
            List of recent messages
        """
        if conversation_id not in self._conversations:
            return []

        # Return last 'limit' messages to maintain context window
        return self._conversations[conversation_id][-limit:]

    def format_messages_for_api(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to API format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]