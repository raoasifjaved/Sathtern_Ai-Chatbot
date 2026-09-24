from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = str(path or settings.database_path)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL DEFAULT 'Conversation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
                    content TEXT NOT NULL,
                    mode TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS project_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, memory_key),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                """
            )

    def create_project(self, name: str, description: str = "") -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO projects(name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (name.strip() or "Untitled Project", description.strip(), now, now),
            )
            project_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO conversations(project_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (project_id, "Main Conversation", now, now),
            )
        return project_id

    def list_projects(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT p.*, COUNT(DISTINCT c.id) AS conversation_count, COUNT(DISTINCT m.id) AS message_count "
                "FROM projects p LEFT JOIN conversations c ON c.project_id=p.id "
                "LEFT JOIN messages m ON m.conversation_id=c.id GROUP BY p.id ORDER BY p.updated_at DESC"
            ).fetchall()

    def get_project(self, project_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()

    def update_project(self, project_id: int, *, name: str | None = None, description: str | None = None) -> None:
        fields: list[str] = []
        values: list[Any] = []
        if name is not None:
            fields.append("name=?")
            values.append(name.strip() or "Untitled Project")
        if description is not None:
            fields.append("description=?")
            values.append(description.strip())
        if not fields:
            return
        fields.append("updated_at=?")
        values.append(utc_now())
        values.append(project_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id=?", values)

    def delete_project(self, project_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def create_conversation(self, project_id: int, title: str = "New Conversation") -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO conversations(project_id,title,created_at,updated_at) VALUES (?,?,?,?)",
                (project_id, title.strip() or "New Conversation", now, now),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
            return int(cur.lastrowid)

    def list_conversations(self, project_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT c.*, COUNT(m.id) AS message_count FROM conversations c "
                "LEFT JOIN messages m ON m.conversation_id=c.id WHERE c.project_id=? "
                "GROUP BY c.id ORDER BY c.updated_at DESC",
                (project_id,),
            ).fetchall()

    def get_conversation(self, conversation_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()

    def add_message(self, conversation_id: int, role: str, content: str, mode: str = "") -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO messages(conversation_id,role,content,mode,created_at) VALUES (?,?,?,?,?)",
                (conversation_id, role, content, mode, now),
            )
            conv = conn.execute("SELECT project_id FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if conv:
                conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
                conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, conv["project_id"]))
            return int(cur.lastrowid)

    def list_messages(self, conversation_id: int, limit: int | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if limit:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?",
                    (conversation_id, limit),
                ).fetchall()
                return list(reversed(rows))
            return conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()

    def search_messages(self, project_id: int, query: str) -> list[sqlite3.Row]:
        pattern = f"%{query.strip()}%"
        with self.connect() as conn:
            return conn.execute(
                "SELECT m.*, c.title AS conversation_title FROM messages m "
                "JOIN conversations c ON c.id=m.conversation_id "
                "WHERE c.project_id=? AND m.content LIKE ? ORDER BY m.created_at DESC LIMIT 30",
                (project_id, pattern),
            ).fetchall()

    def set_memory(self, project_id: int, key: str, value: Any) -> None:
        serialized = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO project_memory(project_id,memory_key,memory_value,updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(project_id,memory_key) DO UPDATE SET memory_value=excluded.memory_value,updated_at=excluded.updated_at",
                (project_id, key, serialized, now),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))

    def get_memory(self, project_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT memory_key,memory_value FROM project_memory WHERE project_id=? ORDER BY memory_key",
                (project_id,),
            ).fetchall()
        result: dict[str, Any] = {}
        for row in rows:
            raw = row["memory_value"]
            try:
                result[row["memory_key"]] = json.loads(raw)
            except json.JSONDecodeError:
                result[row["memory_key"]] = raw
        return result

    def clear_conversation(self, conversation_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
            conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (utc_now(), conversation_id))

    def add_task(self, project_id: int, title: str) -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO tasks(project_id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (project_id, title.strip(), now, now),
            )
            return int(cur.lastrowid)

    def list_tasks(self, project_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY completed ASC, updated_at DESC",
                (project_id,),
            ).fetchall()

    def set_task_completed(self, task_id: int, completed: bool) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE tasks SET completed=?, updated_at=? WHERE id=?",
                (1 if completed else 0, utc_now(), task_id),
            )

    def delete_task(self, task_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))

    def stats(self, project_id: int) -> dict[str, int]:
        with self.connect() as conn:
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.project_id=?",
                (project_id,),
            ).fetchone()[0]
            task_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id=?", (project_id,)).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE project_id=? AND completed=1", (project_id,)
            ).fetchone()[0]
            convs = conn.execute("SELECT COUNT(*) FROM conversations WHERE project_id=?", (project_id,)).fetchone()[0]
        return {"messages": msg_count, "tasks": task_count, "completed_tasks": completed, "conversations": convs}
