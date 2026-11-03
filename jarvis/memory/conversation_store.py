"""Multi-turn conversation store with token budgeting."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from jarvis.core.logger import get_logger
from jarvis.memory.database import get_db_session
from jarvis.memory.models import Conversation, Message

logger = get_logger("JARVIS.ConversationStore")


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation without heavy external dependencies."""
    if not text:
        return 0
    # Average ~4 characters per token for English text and code
    return max(1, len(text) // 4)


class ConversationStore:
    """Manages conversational history, persistence, and token-aware context retrieval."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def db(self):
        if self._session_factory is not None:
            return self._session_factory()
        return get_db_session()

    def get_or_create_conversation(self, conversation_id: str, title: str = "New Conversation") -> Dict[str, Any]:
        """Fetch existing conversation or create a new session."""
        with self.db as session:
            conv = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                conv = Conversation(id=conversation_id, title=title)
                session.add(conv)
                session.commit()
                logger.info(f"Created new conversation session: {conversation_id} ({title})")
            return {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[Dict[str, Any] | List[Any]] = None,
    ) -> Dict[str, Any]:
        """Append a message to the specified conversation."""
        token_count = estimate_tokens(content)
        tool_json = json.dumps(tool_calls) if tool_calls else None

        with self.db as session:
            # Ensure conversation exists
            conv = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                conv = Conversation(id=conversation_id, title=content[:40] if content else "Conversation")
                session.add(conv)

            conv.updated_at = datetime.now(timezone.utc)
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                token_count=token_count,
                tool_calls_json=tool_json,
            )
            session.add(msg)
            session.commit()

            return {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "token_count": msg.token_count,
                "tool_calls": tool_calls,
                "created_at": msg.created_at.isoformat(),
            }

    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20,
        max_tokens: int = 4000,
    ) -> List[Dict[str, Any]]:
        """Retrieve the most recent messages up to a specified token and message budget."""
        with self.db as session:
            messages = (
                session.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(desc(Message.created_at))
                .limit(limit)
                .all()
            )

            # Messages are retrieved in reverse chronological order
            budget_messages = []
            accumulated_tokens = 0

            for msg in messages:
                if accumulated_tokens + msg.token_count > max_tokens and budget_messages:
                    break
                accumulated_tokens += msg.token_count
                tool_calls = json.loads(msg.tool_calls_json) if msg.tool_calls_json else None
                budget_messages.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "token_count": msg.token_count,
                    "tool_calls": tool_calls,
                    "created_at": msg.created_at.isoformat(),
                })

            # Return in chronological order
            budget_messages.reverse()
            return budget_messages

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all conversation sessions ordered by last active."""
        with self.db as session:
            convs = (
                session.query(Conversation)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in convs
            ]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its associated messages."""
        with self.db as session:
            conv = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                session.delete(conv)
                session.commit()
                logger.info(f"Deleted conversation: {conversation_id}")
                return True
            return False


# Singleton conversation store
conversation_store = ConversationStore()
