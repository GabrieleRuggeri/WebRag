import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatStore:
    """Simple SQLite-based store for conversations and messages.

    Schema:
      - conversations(id TEXT PK, user_id TEXT, title TEXT, created_at TEXT, updated_at TEXT, archived INT)
      - messages(id TEXT PK, conversation_id TEXT FK, user_id TEXT, role TEXT, content TEXT, created_at TEXT)
    """

    def __init__(self, db_path: str = "chat_data/chat.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
                ON conversations(user_id, updated_at DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conv_created
                ON messages(conversation_id, created_at)
                """
            )

    # Conversations
    def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        conv_id = str(uuid.uuid4())
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations(id, user_id, title, created_at, updated_at, archived) VALUES(?,?,?,?,?,0)",
                (conv_id, user_id, title, now, now),
            )
        return conv_id

    def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, title, created_at, updated_at, archived FROM conversations WHERE user_id=? AND archived=0 ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = [dict(row) for row in cur.fetchall()]
        return rows

    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, title, created_at, updated_at, archived FROM conversations WHERE id=? AND user_id=?",
                (conversation_id, user_id),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET title=?, updated_at=? WHERE id=? AND user_id=?",
                (title, _utc_now_iso(), conversation_id, user_id),
            )

    def archive_conversation(self, user_id: str, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET archived=1, updated_at=? WHERE id=? AND user_id=?",
                (_utc_now_iso(), conversation_id, user_id),
            )

    # Messages
    def append_message(self, user_id: str, conversation_id: str, role: str, content: str) -> str:
        msg_id = str(uuid.uuid4())
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages(id, conversation_id, user_id, role, content, created_at) VALUES(?,?,?,?,?,?)",
                (msg_id, conversation_id, user_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (now, conversation_id),
            )
        return msg_id

    def get_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, role, content, created_at FROM messages WHERE conversation_id=? AND user_id=? ORDER BY created_at ASC",
                (conversation_id, user_id),
            )
            rows = [dict(row) for row in cur.fetchall()]
        return rows

    def ensure_conversation(self, user_id: str, conversation_id: Optional[str]) -> str:
        """Return a valid conversation id; create if missing/invalid."""
        if conversation_id:
            existing = self.get_conversation(user_id, conversation_id)
            if existing and existing.get("archived") == 0:
                return conversation_id
        return self.create_conversation(user_id)

