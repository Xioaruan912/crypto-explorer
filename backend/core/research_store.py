import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class ResearchStore:
    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reading_list (
                    paper_id TEXT PRIMARY KEY,
                    paper_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'to_read',
                    priority INTEGER NOT NULL DEFAULT 2,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    paper_id TEXT PRIMARY KEY,
                    paper_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    seed_title TEXT NOT NULL DEFAULT '',
                    search_type TEXT NOT NULL DEFAULT 'graph',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            history_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(search_history)").fetchall()
            }
            if "search_type" not in history_columns:
                conn.execute(
                    "ALTER TABLE search_history ADD COLUMN search_type TEXT NOT NULL DEFAULT 'graph'"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    display_name TEXT NOT NULL DEFAULT '研究者',
                    role TEXT NOT NULL DEFAULT '',
                    institution TEXT NOT NULL DEFAULT '',
                    research_interests TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    paper_id TEXT PRIMARY KEY,
                    paper_json TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")

    def list_reading(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reading_list ORDER BY priority ASC, updated_at DESC"
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def upsert_reading(
        self,
        paper: dict[str, Any],
        status: str = "to_read",
        priority: int = 2,
        note: str = "",
    ) -> dict[str, Any]:
        paper_id = str(paper["id"])
        payload = json.dumps(paper, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reading_list (paper_id, paper_json, status, priority, note)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                  paper_json = excluded.paper_json,
                  status = excluded.status,
                  priority = excluded.priority,
                  note = excluded.note,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (paper_id, payload, status, priority, note),
            )
            row = conn.execute(
                "SELECT * FROM reading_list WHERE paper_id = ?", (paper_id,)
            ).fetchone()
        return self._row_to_item(row)

    def update_reading(self, paper_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"status", "priority", "note"}
        updates = {key: value for key, value in fields.items() if key in allowed and value is not None}
        if not updates:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM reading_list WHERE paper_id = ?", (paper_id,)).fetchone()
            return self._row_to_item(row) if row else None

        assignments = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [paper_id]
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE reading_list SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE paper_id = ?",
                values,
            )
            row = conn.execute("SELECT * FROM reading_list WHERE paper_id = ?", (paper_id,)).fetchone()
        return self._row_to_item(row) if row else None

    def delete_reading(self, paper_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM reading_list WHERE paper_id = ?", (paper_id,))
            return cur.rowcount > 0

    def list_favorites(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM favorites ORDER BY created_at DESC").fetchall()
        return [
            {"paper": json.loads(row["paper_json"]), "created_at": row["created_at"]}
            for row in rows
        ]

    def upsert_favorite(self, paper: dict[str, Any]) -> dict[str, Any]:
        paper_id = str(paper["id"])
        payload = json.dumps(paper, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO favorites (paper_id, paper_json) VALUES (?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET paper_json = excluded.paper_json
                """,
                (paper_id, payload),
            )
            row = conn.execute("SELECT * FROM favorites WHERE paper_id = ?", (paper_id,)).fetchone()
        return {"paper": json.loads(row["paper_json"]), "created_at": row["created_at"]}

    def delete_favorite(self, paper_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM favorites WHERE paper_id = ?", (paper_id,))
            return cur.rowcount > 0

    def list_notes(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
        return [self._row_to_note(row) for row in rows]

    def get_note(self, paper_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notes WHERE paper_id = ?", (paper_id,)).fetchone()
        return self._row_to_note(row) if row else None

    def upsert_note(self, paper: dict[str, Any], title: str, content: str) -> dict[str, Any]:
        paper_id = str(paper["id"])
        payload = json.dumps(paper, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notes (paper_id, paper_json, title, content)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                  paper_json = excluded.paper_json,
                  title = excluded.title,
                  content = excluded.content,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (paper_id, payload, title, content),
            )
            row = conn.execute("SELECT * FROM notes WHERE paper_id = ?", (paper_id,)).fetchone()
        return self._row_to_note(row)

    def delete_note(self, paper_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM notes WHERE paper_id = ?", (paper_id,))
            return cur.rowcount > 0

    def add_search_history(
        self,
        query: str,
        result_count: int,
        seed_title: str = "",
        search_type: str = "graph",
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO search_history (query, result_count, seed_title, search_type) VALUES (?, ?, ?, ?)",
                (query, result_count, seed_title, search_type),
            )
            row = conn.execute("SELECT * FROM search_history WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def list_search_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_search_history(self, history_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM search_history WHERE id = ?", (history_id,))
            return cur.rowcount > 0

    def clear_search_history(self) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM search_history")
            return cur.rowcount

    def get_profile(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        return dict(row)

    def update_profile(self, fields: dict[str, Any]) -> dict[str, Any]:
        allowed = {"display_name", "role", "institution", "research_interests"}
        updates = {key: value for key, value in fields.items() if key in allowed and value is not None}
        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values())
            with self._lock, self._connect() as conn:
                conn.execute(
                    f"UPDATE user_profile SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                    values,
                )
        return self.get_profile()

    def dashboard(self) -> dict[str, Any]:
        with self._connect() as conn:
            reading_count = conn.execute("SELECT COUNT(*) FROM reading_list").fetchone()[0]
            favorite_count = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
            history_count = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
            note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            statuses = {
                row["status"]: row["count"]
                for row in conn.execute(
                    "SELECT status, COUNT(*) AS count FROM reading_list GROUP BY status"
                ).fetchall()
            }
            recent = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM search_history ORDER BY id DESC LIMIT 5"
                ).fetchall()
            ]
        return {
            "reading_count": reading_count,
            "favorite_count": favorite_count,
            "history_count": history_count,
            "note_count": note_count,
            "reading_statuses": statuses,
            "recent_searches": recent,
        }

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "paper": json.loads(row["paper_json"]),
            "status": row["status"],
            "priority": row["priority"],
            "note": row["note"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "paper": json.loads(row["paper_json"]),
            "title": row["title"],
            "content": row["content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
