"""Semantic memory store for long-term facts, preferences, notes, and reminders."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import desc
from jarvis.core.logger import get_logger
from jarvis.memory.database import get_db_session
from jarvis.memory.models import Contact, Note, Reminder, UserFact

logger = get_logger("JARVIS.SemanticStore")


class SemanticMemoryStore:
    """Manages long-term declarative facts, user preferences, notes, and reminders."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def db(self):
        if self._session_factory is not None:
            return self._session_factory()
        return get_db_session()

    # --- Facts & Preferences ---

    def set_fact(
        self,
        key: str,
        value: str,
        category: str = "preference",
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Store or update a learned fact or user preference."""
        normalized_key = key.strip().lower()
        with self.db as session:
            fact = session.query(UserFact).filter(UserFact.key == normalized_key).first()
            if fact:
                fact.value = value
                fact.category = category
                fact.confidence = confidence
                fact.updated_at = datetime.now(timezone.utc)
            else:
                fact = UserFact(
                    key=normalized_key,
                    value=value,
                    category=category,
                    confidence=confidence,
                )
                session.add(fact)
            session.commit()
            logger.info(f"Stored fact [{category}] {normalized_key} = {value}")
            return {
                "id": fact.id,
                "key": fact.key,
                "value": fact.value,
                "category": fact.category,
                "confidence": fact.confidence,
            }

    def get_fact(self, key: str) -> Optional[str]:
        """Retrieve a specific fact by key."""
        normalized_key = key.strip().lower()
        with self.db as session:
            fact = session.query(UserFact).filter(UserFact.key == normalized_key).first()
            return fact.value if fact else None

    def delete_fact(self, key: str) -> bool:
        """Delete a fact by key."""
        normalized_key = key.strip().lower()
        with self.db as session:
            fact = session.query(UserFact).filter(UserFact.key == normalized_key).first()
            if fact:
                session.delete(fact)
                session.commit()
                return True
            return False

    def list_facts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all stored facts, optionally filtered by category."""
        with self.db as session:
            query = session.query(UserFact)
            if category:
                query = query.filter(UserFact.category == category)
            facts = query.order_by(UserFact.key).all()
            return [
                {
                    "key": f.key,
                    "value": f.value,
                    "category": f.category,
                    "confidence": f.confidence,
                }
                for f in facts
            ]

    def search_facts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search facts by query relevance using term overlap."""
        if not query:
            return []
        query_terms = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
        with self.db as session:
            all_facts = session.query(UserFact).all()
            scored_facts = []
            for f in all_facts:
                combined_text = f"{f.key.replace('_', ' ')} {f.value} {f.category}"
                fact_terms = set(re.findall(r"[a-zA-Z0-9]+", combined_text.lower()))
                overlap = len(query_terms.intersection(fact_terms))
                if overlap > 0:
                    scored_facts.append((overlap, f))

            scored_facts.sort(key=lambda x: x[0], reverse=True)
            return [
                {
                    "key": f.key,
                    "value": f.value,
                    "category": f.category,
                    "relevance_score": score,
                }
                for score, f in scored_facts[:limit]
            ]

    def get_context_prompt(self, limit: int = 15) -> str:
        """Generate formatted prompt string of high-confidence facts for LLM injection."""
        facts = self.list_facts()
        if not facts:
            return ""
        lines = ["--- User Profile & Known Preferences ---"]
        for f in facts[:limit]:
            lines.append(f"- {f['key'].replace('_', ' ').title()}: {f['value']}")
        return "\n".join(lines)

    # --- Contacts Management ---

    def add_contact(
        self,
        name: str,
        phone: str,
        email: str = "",
        relationship: str = "contact",
    ) -> Dict[str, Any]:
        """Save or update contact information."""
        normalized_name = name.strip()
        with self.db as session:
            contact = session.query(Contact).filter(Contact.name.ilike(normalized_name)).first()
            if contact:
                contact.phone = phone
                contact.email = email
                contact.relationship = relationship
            else:
                contact = Contact(
                    name=normalized_name,
                    phone=phone,
                    email=email,
                    relationship=relationship,
                )
                session.add(contact)
            session.commit()
            logger.info(f"Saved contact '{normalized_name}' -> Phone: {phone}")
            return {
                "id": contact.id,
                "name": contact.name,
                "phone": contact.phone,
                "email": contact.email,
                "relationship": contact.relationship,
            }

    def get_contact_by_name(self, name_query: str) -> Optional[Dict[str, Any]]:
        """Look up contact by name (case-insensitive substring or match)."""
        clean_q = name_query.strip().lower()
        with self.db as session:
            contacts = session.query(Contact).all()
            for c in contacts:
                if clean_q in c.name.lower() or c.name.lower() in clean_q:
                    return {
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "email": c.email,
                        "relationship": c.relationship,
                    }
            return None

    def list_contacts(self) -> List[Dict[str, Any]]:
        """List all saved contacts."""
        with self.db as session:
            contacts = session.query(Contact).order_by(Contact.name).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "email": c.email,
                    "relationship": c.relationship,
                }
                for c in contacts
            ]

    # --- Notes ---

    def create_note(self, title: str, content: str, tags: str = "", is_pinned: bool = False) -> Dict[str, Any]:
        """Create a new note."""
        with self.db as session:
            note = Note(title=title, content=content, tags=tags, is_pinned=is_pinned)
            session.add(note)
            session.commit()
            return {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "is_pinned": note.is_pinned,
                "created_at": note.created_at.isoformat(),
            }

    def list_notes(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List notes, optionally filtered by tag, ordered by pinned first then recent."""
        with self.db as session:
            query = session.query(Note)
            if tag:
                query = query.filter(Note.tags.like(f"%{tag}%"))
            notes = query.order_by(desc(Note.is_pinned), desc(Note.updated_at)).all()
            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "content": n.content,
                    "tags": n.tags,
                    "is_pinned": n.is_pinned,
                    "updated_at": n.updated_at.isoformat(),
                }
                for n in notes
            ]

    def delete_note(self, note_id: str) -> bool:
        """Delete a note by ID."""
        with self.db as session:
            note = session.query(Note).filter(Note.id == note_id).first()
            if note:
                session.delete(note)
                session.commit()
                return True
            return False

    # --- Reminders ---

    def add_reminder(
        self,
        title: str,
        due_at: datetime,
        description: str = "",
        recurrence: str = "none",
    ) -> Dict[str, Any]:
        """Add a scheduled reminder."""
        with self.db as session:
            rem = Reminder(
                title=title,
                description=description,
                due_at=due_at,
                recurrence=recurrence,
            )
            session.add(rem)
            session.commit()
            return {
                "id": rem.id,
                "title": rem.title,
                "description": rem.description,
                "due_at": rem.due_at.isoformat(),
                "is_completed": rem.is_completed,
                "recurrence": rem.recurrence,
            }

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """List active reminders that are not yet marked as completed."""
        with self.db as session:
            rems = (
                session.query(Reminder)
                .filter(Reminder.is_completed == False)
                .order_by(Reminder.due_at)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "description": r.description,
                    "due_at": r.due_at.isoformat(),
                    "recurrence": r.recurrence,
                }
                for r in rems
            ]

    def mark_reminder_completed(self, reminder_id: str) -> bool:
        """Mark a reminder as completed."""
        with self.db as session:
            rem = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            if rem:
                rem.is_completed = True
                session.commit()
                return True
            return False


# Singleton semantic store
semantic_store = SemanticMemoryStore()
