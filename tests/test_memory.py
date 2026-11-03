"""Unit tests for JARVIS Memory and Persistence subsystem."""

from datetime import datetime, timezone, timedelta
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jarvis.memory.models import Base
from jarvis.memory.database import init_db
from jarvis.memory.conversation_store import ConversationStore, estimate_tokens
from jarvis.memory.semantic_store import SemanticMemoryStore


class TestMemory(unittest.TestCase):
    """Test suite for conversation persistence, semantic facts, notes, and reminders."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp_dir.name) / "test_memory.db"
        cls.engine = create_engine(f"sqlite:///{cls.db_path.as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)

        cls.session_factory = sessionmaker(bind=cls.engine)

        # Patch stores to use test db
        cls.conv_store = ConversationStore(session_factory=cls.get_test_session)
        cls.sem_store = SemanticMemoryStore(session_factory=cls.get_test_session)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        cls.tmp_dir.cleanup()

    @classmethod
    def get_test_session(cls):
        from contextlib import contextmanager
        @contextmanager
        def _session_ctx():
            session = cls.session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return _session_ctx()

    def test_estimate_tokens(self):
        """Verify token estimation logic."""
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("Hello world"), 2)
        long_text = "a" * 400
        self.assertEqual(estimate_tokens(long_text), 100)

    def test_conversation_and_messages(self):
        """Verify multi-turn message persistence and token budgeting."""
        conv_id = "test_session_1"
        self.conv_store.get_or_create_conversation(conv_id, "Test Conversation")

        # Add user and assistant messages
        self.conv_store.add_message(conv_id, "user", "Hello JARVIS, open Chrome.")
        self.conv_store.add_message(conv_id, "assistant", "Opening Google Chrome for you now, Sir.")
        self.conv_store.add_message(conv_id, "user", "What is my battery level?")
        self.conv_store.add_message(conv_id, "assistant", "Your battery is currently at 85%.")

        messages = self.conv_store.get_recent_messages(conv_id, limit=10, max_tokens=1000)
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello JARVIS, open Chrome.")
        self.assertEqual(messages[3]["role"], "assistant")
        self.assertEqual(messages[3]["content"], "Your battery is currently at 85%.")

        # Test token budget clipping
        tiny_budget_msgs = self.conv_store.get_recent_messages(conv_id, limit=10, max_tokens=15)
        self.assertLessEqual(len(tiny_budget_msgs), 2)

    def test_semantic_facts_and_search(self):
        """Verify user fact storage, retrieval, and term overlap search."""
        self.sem_store.set_fact("preferred_browser", "Google Chrome", category="preference")
        self.sem_store.set_fact("user_role", "Principal Software Engineer", category="personal")

        val = self.sem_store.get_fact("preferred_browser")
        self.assertEqual(val, "Google Chrome")

        # Search
        results = self.sem_store.search_facts("What browser does the user like?")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["key"], "preferred_browser")

        # Context prompt string
        prompt = self.sem_store.get_context_prompt()
        self.assertIn("Google Chrome", prompt)
        self.assertIn("Principal Software Engineer", prompt)

    def test_notes_and_reminders(self):
        """Verify notes creation and reminder completion."""
        # Notes
        note = self.sem_store.create_note("Project Architecture", "Use modular event-driven layers.", tags="work,arch")
        notes = self.sem_store.list_notes(tag="work")
        self.assertTrue(any(n["id"] == note["id"] for n in notes))

        # Reminders
        due = datetime.now(timezone.utc) + timedelta(hours=2)
        rem = self.sem_store.add_reminder("Review pull requests", due_at=due)
        pending = self.sem_store.get_pending_reminders()
        self.assertTrue(any(r["id"] == rem["id"] for r in pending))

        self.sem_store.mark_reminder_completed(rem["id"])
        pending_after = self.sem_store.get_pending_reminders()
        self.assertFalse(any(r["id"] == rem["id"] for r in pending_after))


if __name__ == "__main__":
    unittest.main()
