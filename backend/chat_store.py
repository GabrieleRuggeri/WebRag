import os
import csv
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

    def debug_print_all(self, max_content_len: int = 1000) -> None:
        """Pretty print all conversations and messages for quick debugging.

        Prints all conversations (any user, including archived) ordered by
        most recently updated, and their messages ordered by creation time.

        Args:
            max_content_len: Maximum characters of message content to display.
        """
        with self._connect() as conn:
            # Fetch conversations and messages in two queries for speed.
            conv_rows = conn.execute(
                """
                SELECT id, user_id, title, created_at, updated_at, archived
                FROM conversations
                ORDER BY updated_at DESC
                """
            ).fetchall()

            msg_rows = conn.execute(
                """
                SELECT id, conversation_id, user_id, role, content, created_at
                FROM messages
                ORDER BY created_at ASC
                """
            ).fetchall()

        # Group messages by conversation id
        messages_by_conv: Dict[str, List[sqlite3.Row]] = {}
        for r in msg_rows:
            messages_by_conv.setdefault(r["conversation_id"], []).append(r)

        print("=== ChatStore Debug Dump ===")
        print(f"Conversations: {len(conv_rows)}")
        for idx, conv in enumerate(conv_rows, start=1):
            conv_id = conv["id"]
            user = conv["user_id"]
            archived = int(conv["archived"]) if conv["archived"] is not None else 0
            created = conv["created_at"]
            updated = conv["updated_at"]

            print(
                f"\n[{idx}] Conversation {conv_id} | user={user} | archived={archived}\n"
                f"    title=""{title}""\n"
                f"    created_at={created}\n"
                f"    updated_at={updated}"
            )

            msgs = messages_by_conv.get(conv_id, [])
            print(f"    messages ({len(msgs)}):")
            for m in msgs:
                ts = m["created_at"]
                role = m["role"]
                m_user = m["user_id"]
                content = m["content"] or ""
                if max_content_len and len(content) > max_content_len:
                    content = content[: max_content_len - 1] + "…"
                print(f"      - [{ts}] {role}@{m_user}: {content}")

    def export_csv(
        self,
        out_path: Optional[str] = None,
        include_archived: bool = True,
        max_content_len: Optional[int] = None,
    ) -> str:
        """Export conversations and messages to a single CSV file.

        Each row contains conversation metadata and a message (if any).
        Conversations without messages are still included with empty message fields.

        Args:
            out_path: Destination CSV path. Defaults to chat_data/chat_export.csv
            include_archived: Whether to include archived conversations.
            max_content_len: If provided, truncate message content to this length.

        Returns:
            The path to the written CSV file.
        """
        if out_path is None:
            out_dir = os.path.dirname(self.db_path) or "."
            out_path = os.path.join(out_dir, "chat_export.csv")

        query = (
            "SELECT c.id AS conv_id, c.user_id AS conv_user_id, c.title AS conv_title, "
            "c.created_at AS conv_created_at, c.updated_at AS conv_updated_at, c.archived AS conv_archived, "
            "m.id AS msg_id, m.user_id AS msg_user_id, m.role AS msg_role, m.content AS msg_content, m.created_at AS msg_created_at "
            "FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id "
        )
        params: tuple = ()
        if include_archived:
            query += "ORDER BY c.updated_at DESC, m.created_at ASC"
        else:
            query += "WHERE c.archived = 0 ORDER BY c.updated_at DESC, m.created_at ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        fieldnames = [
            "conv_id",
            "conv_user_id",
            "conv_title",
            "conv_created_at",
            "conv_updated_at",
            "conv_archived",
            "msg_id",
            "msg_user_id",
            "msg_role",
            "msg_content",
            "msg_created_at",
        ]

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                content = r["msg_content"] if r["msg_content"] is not None else ""
                if max_content_len is not None and max_content_len >= 0 and len(content) > max_content_len:
                    content = content[: max_content_len]
                writer.writerow(
                    {
                        "conv_id": r["conv_id"],
                        "conv_user_id": r["conv_user_id"],
                        "conv_title": r["conv_title"],
                        "conv_created_at": r["conv_created_at"],
                        "conv_updated_at": r["conv_updated_at"],
                        "conv_archived": r["conv_archived"],
                        "msg_id": r["msg_id"],
                        "msg_user_id": r["msg_user_id"],
                        "msg_role": r["msg_role"],
                        "msg_content": content,
                        "msg_created_at": r["msg_created_at"],
                    }
                )

        return out_path

if __name__ == "__main__":
    store = ChatStore()
