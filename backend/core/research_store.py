import json
import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
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
            # Uvicorn runs multiple worker processes. Serialize schema creation/migrations so
            # two workers cannot both observe an old schema and race on the same ALTER TABLE.
            conn.execute("BEGIN IMMEDIATE")
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
                    effective_query TEXT NOT NULL DEFAULT '',
                    query_language TEXT NOT NULL DEFAULT 'unknown',
                    language_mode TEXT NOT NULL DEFAULT 'original',
                    normalized_terms_json TEXT NOT NULL DEFAULT '[]',
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
            if "effective_query" not in history_columns:
                conn.execute("ALTER TABLE search_history ADD COLUMN effective_query TEXT NOT NULL DEFAULT ''")
            if "query_language" not in history_columns:
                conn.execute("ALTER TABLE search_history ADD COLUMN query_language TEXT NOT NULL DEFAULT 'unknown'")
            if "language_mode" not in history_columns:
                conn.execute("ALTER TABLE search_history ADD COLUMN language_mode TEXT NOT NULL DEFAULT 'original'")
            if "normalized_terms_json" not in history_columns:
                conn.execute("ALTER TABLE search_history ADD COLUMN normalized_terms_json TEXT NOT NULL DEFAULT '[]'")
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reading_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL,
                    task_type TEXT NOT NULL DEFAULT 'read',
                    task_text TEXT NOT NULL DEFAULT '阅读论文',
                    scheduled_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'todo',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES reading_list(paper_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reading_tasks_scheduled_date ON reading_tasks(scheduled_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reading_tasks_paper_id ON reading_tasks(paper_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_draw_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    paper_json TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_paper_draw_history_id ON paper_draw_history(id DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS genealogy_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_user (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    failed_login_count INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at)")
            auth_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(auth_user)").fetchall()
            }
            if "failed_login_count" not in auth_columns:
                conn.execute("ALTER TABLE auth_user ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0")
            if "locked_until" not in auth_columns:
                conn.execute("ALTER TABLE auth_user ADD COLUMN locked_until TEXT")
            conn.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")
            user = conn.execute("SELECT id FROM auth_user WHERE id = 1").fetchone()
            if user is None:
                conn.execute(
                    "INSERT INTO auth_user (id, username, password_hash, must_change_password) VALUES (1, ?, ?, 1)",
                    ("admin", self.hash_password("123456")),
                )

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
        with self._lock, self._connect() as conn:
            current = conn.execute(
                "SELECT * FROM reading_list WHERE paper_id = ?", (paper_id,)
            ).fetchone()
            if current is None:
                return None
            status = fields.get("status") if fields.get("status") is not None else current["status"]
            priority = fields.get("priority") if fields.get("priority") is not None else current["priority"]
            note = fields.get("note") if fields.get("note") is not None else current["note"]
            conn.execute(
                """
                UPDATE reading_list
                SET status = ?, priority = ?, note = ?, updated_at = CURRENT_TIMESTAMP
                WHERE paper_id = ?
                """,
                (status, priority, note, paper_id),
            )
            row = conn.execute("SELECT * FROM reading_list WHERE paper_id = ?", (paper_id,)).fetchone()
        return self._row_to_item(row) if row else None

    def delete_reading(self, paper_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM reading_list WHERE paper_id = ?", (paper_id,))
            return cur.rowcount > 0

    def list_reading_tasks(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task.*, reading.paper_json
                FROM reading_tasks AS task
                JOIN reading_list AS reading ON reading.paper_id = task.paper_id
                WHERE task.scheduled_date >= ? AND task.scheduled_date <= ?
                ORDER BY task.scheduled_date ASC,
                         CASE task.status WHEN 'doing' THEN 0 WHEN 'todo' THEN 1 ELSE 2 END,
                         task.id ASC
                """,
                (from_date, to_date),
            ).fetchall()
        return [self._row_to_reading_task(row) for row in rows]

    def create_reading_task(
        self,
        paper_id: str,
        scheduled_date: str,
        task_type: str,
        task_text: str,
        status: str = "todo",
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            paper_row = conn.execute(
                "SELECT paper_json FROM reading_list WHERE paper_id = ?", (paper_id,)
            ).fetchone()
            if paper_row is None:
                return None
            cur = conn.execute(
                """
                INSERT INTO reading_tasks (paper_id, task_type, task_text, scheduled_date, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (paper_id, task_type, task_text, scheduled_date, status),
            )
            row = conn.execute(
                """
                SELECT task.*, reading.paper_json
                FROM reading_tasks AS task
                JOIN reading_list AS reading ON reading.paper_id = task.paper_id
                WHERE task.id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
        return self._row_to_reading_task(row)

    def update_reading_task(self, task_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            current = conn.execute("SELECT * FROM reading_tasks WHERE id = ?", (task_id,)).fetchone()
            if current is None:
                return None
            scheduled_date = fields.get("scheduled_date") if fields.get("scheduled_date") is not None else current["scheduled_date"]
            task_type = fields.get("task_type") if fields.get("task_type") is not None else current["task_type"]
            task_text = fields.get("task_text") if fields.get("task_text") is not None else current["task_text"]
            status = fields.get("status") if fields.get("status") is not None else current["status"]
            conn.execute(
                """
                UPDATE reading_tasks
                SET scheduled_date = ?, task_type = ?, task_text = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (scheduled_date, task_type, task_text, status, task_id),
            )
            row = conn.execute(
                """
                SELECT task.*, reading.paper_json
                FROM reading_tasks AS task
                JOIN reading_list AS reading ON reading.paper_id = task.paper_id
                WHERE task.id = ?
                """,
                (task_id,),
            ).fetchone()
        return self._row_to_reading_task(row) if row else None

    def delete_reading_task(self, task_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM reading_tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def add_draw_history(self, query: str, paper: dict[str, Any], reason: str) -> dict[str, Any]:
        paper_id = str(paper.get("paperId") or paper.get("id") or "").strip()
        if not paper_id:
            raise ValueError("paper id is required")
        payload = json.dumps(paper, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO paper_draw_history (query, paper_id, paper_json, reason) VALUES (?, ?, ?, ?)",
                (query, paper_id, payload, reason),
            )
            conn.execute(
                "DELETE FROM paper_draw_history WHERE id NOT IN (SELECT id FROM paper_draw_history ORDER BY id DESC LIMIT 500)"
            )
            row = conn.execute(
                "SELECT * FROM paper_draw_history WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
        return self._row_to_draw(row)

    def list_draw_history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM paper_draw_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_draw(row) for row in rows]

    def clear_draw_history(self) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM paper_draw_history")
            return cur.rowcount

    def get_genealogy_cache(self, cache_key: str, max_age_hours: int | None = 24) -> dict[str, Any] | None:
        with self._connect() as conn:
            if max_age_hours is None:
                row = conn.execute(
                    "SELECT payload_json FROM genealogy_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload_json FROM genealogy_cache
                    WHERE cache_key = ? AND updated_at >= datetime('now', ?)
                    """,
                    (cache_key, f"-{max(1, max_age_hours)} hours"),
                ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row["payload_json"])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def upsert_genealogy_cache(self, cache_key: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO genealogy_cache (cache_key, payload_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(cache_key) DO UPDATE SET
                  payload_json = excluded.payload_json,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (cache_key, encoded),
            )
            conn.execute(
                "DELETE FROM genealogy_cache WHERE cache_key NOT IN (SELECT cache_key FROM genealogy_cache ORDER BY updated_at DESC LIMIT 100)"
            )

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
        query_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query_info = query_info or {}
        effective_query = str(query_info.get("effectiveQuery") or query)
        query_language = str(query_info.get("detectedLanguage") or "unknown")
        language_mode = str(query_info.get("requestedMode") or "original")
        normalized_terms = query_info.get("normalizedTerms") or [effective_query]
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO search_history
                  (query, effective_query, query_language, language_mode, normalized_terms_json, result_count, seed_title, search_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query,
                    effective_query,
                    query_language,
                    language_mode,
                    json.dumps(normalized_terms, ensure_ascii=False),
                    result_count,
                    seed_title,
                    search_type,
                ),
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
        with self._lock, self._connect() as conn:
            current = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
            display_name = fields.get("display_name") if fields.get("display_name") is not None else current["display_name"]
            role = fields.get("role") if fields.get("role") is not None else current["role"]
            institution = fields.get("institution") if fields.get("institution") is not None else current["institution"]
            research_interests = fields.get("research_interests") if fields.get("research_interests") is not None else current["research_interests"]
            conn.execute(
                """
                UPDATE user_profile
                SET display_name = ?, role = ?, institution = ?, research_interests = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (display_name, role, institution, research_interests),
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
    def hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$", 5)
            if algorithm != "scrypt":
                return False
            digest = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=32,
            )
            return hmac.compare_digest(digest.hex(), digest_hex)
        except (ValueError, TypeError):
            return False

    def authenticate(self, username: str, password: str) -> tuple[str, dict[str, Any] | None]:
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM auth_user WHERE id = 1").fetchone()
            if row is None:
                return "invalid", None
            # Always run the password KDF, even when the username is wrong. This
            # avoids a cheap username-enumeration timing signal. A valid login is
            # also allowed to recover from an attacker-triggered lockout, while
            # wrong guesses remain throttled.
            username_valid = hmac.compare_digest(str(row["username"]), username)
            password_valid = self.verify_password(password, row["password_hash"])
            valid = username_valid and password_valid
            locked_until = row["locked_until"]
            if locked_until:
                try:
                    if datetime.fromisoformat(locked_until) > now and not valid:
                        return "locked", None
                except ValueError:
                    pass
            if not valid:
                failures = int(row["failed_login_count"] or 0) + 1
                next_locked_until = None
                if failures >= 5:
                    next_locked_until = (now + timedelta(minutes=15)).isoformat()
                    failures = 0
                conn.execute(
                    "UPDATE auth_user SET failed_login_count = ?, locked_until = ? WHERE id = 1",
                    (failures, next_locked_until),
                )
                return "invalid", None
            conn.execute(
                "UPDATE auth_user SET failed_login_count = 0, locked_until = NULL WHERE id = 1"
            )
        return "ok", {
            "username": row["username"],
            "must_change_password": bool(row["must_change_password"]),
        }

    def create_session(self, ttl_hours: int = 24) -> tuple[str, dict[str, Any]]:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=ttl_hours)
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now.isoformat(),))
            conn.execute(
                "INSERT INTO auth_sessions (token_hash, csrf_token, created_at, expires_at, last_seen_at) VALUES (?, ?, ?, ?, ?)",
                (token_hash, csrf_token, now.isoformat(), expires.isoformat(), now.isoformat()),
            )
        return token, {"csrf_token": csrf_token, "expires_at": expires.isoformat()}

    def get_session(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM auth_sessions WHERE token_hash = ?", (token_hash,)).fetchone()
            if row is None:
                return None
            try:
                expires = datetime.fromisoformat(row["expires_at"])
            except ValueError:
                return None
            if expires <= now:
                conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
                return None
            conn.execute(
                "UPDATE auth_sessions SET last_seen_at = ? WHERE token_hash = ?",
                (now.isoformat(), token_hash),
            )
            user = conn.execute("SELECT username, must_change_password FROM auth_user WHERE id = 1").fetchone()
        return {
            "token_hash": token_hash,
            "csrf_token": row["csrf_token"],
            "expires_at": row["expires_at"],
            "username": user["username"],
            "must_change_password": bool(user["must_change_password"]),
        }

    def delete_session(self, token: str) -> None:
        if not token:
            return
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))

    def delete_all_sessions(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_sessions")

    def get_account(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            row = conn.execute("SELECT username, must_change_password, updated_at FROM auth_user WHERE id = 1").fetchone()
            session_count = conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0]
        return {
            "username": row["username"],
            "must_change_password": bool(row["must_change_password"]),
            "updated_at": row["updated_at"],
            "active_sessions": session_count,
        }

    def update_credentials(self, current_password: str, username: str | None, new_password: str | None) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM auth_user WHERE id = 1").fetchone()
            if row is None or not self.verify_password(current_password, row["password_hash"]):
                return None
            next_username = username.strip() if username is not None else row["username"]
            next_hash = self.hash_password(new_password) if new_password else row["password_hash"]
            must_change = 0 if new_password else row["must_change_password"]
            conn.execute(
                "UPDATE auth_user SET username = ?, password_hash = ?, must_change_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (next_username, next_hash, must_change),
            )
        return self.get_account()

    def export_backup(self) -> dict[str, Any]:
        with self._connect() as conn:
            tables = {
                "reading_list": [dict(row) for row in conn.execute("SELECT * FROM reading_list").fetchall()],
                "reading_tasks": [dict(row) for row in conn.execute("SELECT * FROM reading_tasks").fetchall()],
                "favorites": [dict(row) for row in conn.execute("SELECT * FROM favorites").fetchall()],
                "search_history": [dict(row) for row in conn.execute("SELECT * FROM search_history").fetchall()],
                "user_profile": [dict(row) for row in conn.execute("SELECT * FROM user_profile").fetchall()],
                "notes": [dict(row) for row in conn.execute("SELECT * FROM notes").fetchall()],
                "paper_draw_history": [dict(row) for row in conn.execute("SELECT * FROM paper_draw_history").fetchall()],
            }
        return {
            "format": "crypto-explorer-backup",
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tables": tables,
        }

    def import_backup(self, backup: dict[str, Any]) -> dict[str, int]:
        if backup.get("format") != "crypto-explorer-backup" or backup.get("version") != 1:
            raise ValueError("unsupported backup format")
        tables = backup.get("tables")
        if not isinstance(tables, dict):
            raise ValueError("invalid backup tables")
        allowed_columns = {
            "reading_list": ["paper_id", "paper_json", "status", "priority", "note", "created_at", "updated_at"],
            "reading_tasks": ["id", "paper_id", "task_type", "task_text", "scheduled_date", "status", "created_at", "updated_at"],
            "favorites": ["paper_id", "paper_json", "created_at"],
            "search_history": [
                "id", "query", "effective_query", "query_language", "language_mode",
                "normalized_terms_json", "result_count", "seed_title", "search_type", "created_at",
            ],
            "user_profile": ["id", "display_name", "role", "institution", "research_interests", "updated_at"],
            "notes": ["paper_id", "paper_json", "title", "content", "created_at", "updated_at"],
            "paper_draw_history": ["id", "query", "paper_id", "paper_json", "reason", "created_at"],
        }
        unknown_tables = set(tables) - set(allowed_columns)
        if unknown_tables:
            raise ValueError("backup contains unsupported tables")
        normalized: dict[str, list[dict[str, Any]]] = {}
        total_rows = 0
        for table, columns in allowed_columns.items():
            rows = tables.get(table, [])
            if not isinstance(rows, list) or len(rows) > 10000:
                raise ValueError(f"invalid backup table: {table}")
            normalized[table] = []
            for row in rows:
                if not isinstance(row, dict) or any(key not in columns for key in row):
                    raise ValueError(f"invalid backup row: {table}")
                item = {column: row.get(column) for column in columns}
                if table == "search_history":
                    item["effective_query"] = str(item.get("effective_query") or item.get("query") or "")
                    item["query_language"] = str(item.get("query_language") or "unknown")
                    item["language_mode"] = str(item.get("language_mode") or "original")
                    item["normalized_terms_json"] = str(item.get("normalized_terms_json") or "[]")
                if "paper_json" in item and item["paper_json"] is not None:
                    parsed = json.loads(item["paper_json"])
                    parsed_id = str(parsed.get("id") or parsed.get("paperId") or "").strip() if isinstance(parsed, dict) else ""
                    if not isinstance(parsed, dict) or not parsed_id:
                        raise ValueError(f"invalid paper payload: {table}")
                    if str(item.get("paper_id", "")) != parsed_id:
                        raise ValueError(f"paper id mismatch: {table}")
                normalized[table].append(item)
                total_rows += 1
                if total_rows > 20000:
                    raise ValueError("backup contains too many rows")

        reading_ids = {str(row["paper_id"]) for row in normalized["reading_list"]}
        for row in normalized["reading_list"]:
            if row["status"] not in {"to_read", "reading", "done"}:
                raise ValueError("invalid reading status")
            if row["priority"] not in {1, 2, 3}:
                raise ValueError("invalid reading priority")
            if not isinstance(row["note"], str) or len(row["note"]) > 4000:
                raise ValueError("invalid reading note")
        seen_task_ids: set[int] = set()
        for row in normalized["reading_tasks"]:
            if not isinstance(row["id"], int) or row["id"] <= 0 or row["id"] in seen_task_ids:
                raise ValueError("invalid reading task id")
            seen_task_ids.add(row["id"])
            if str(row["paper_id"]) not in reading_ids:
                raise ValueError("reading task references missing paper")
            if row["task_type"] not in {"read", "notes", "review", "reproduce", "custom"}:
                raise ValueError("invalid reading task type")
            if row["status"] not in {"todo", "doing", "done"}:
                raise ValueError("invalid reading task status")
            if not isinstance(row["task_text"], str) or not row["task_text"].strip() or len(row["task_text"]) > 500:
                raise ValueError("invalid reading task text")
            try:
                datetime.strptime(str(row["scheduled_date"]), "%Y-%m-%d")
            except ValueError as error:
                raise ValueError("invalid reading task date") from error
        for row in normalized["search_history"]:
            if row["search_type"] not in {"graph", "papers", "authors", "venues"}:
                raise ValueError("invalid history type")
            if not isinstance(row["query"], str) or len(row["query"]) > 300:
                raise ValueError("invalid history query")
            if not isinstance(row["effective_query"], str) or len(row["effective_query"]) > 500:
                raise ValueError("invalid effective history query")
            if row["query_language"] not in {"zh", "en", "mixed", "unknown"}:
                raise ValueError("invalid history query language")
            if row["language_mode"] not in {"academic_en", "original"}:
                raise ValueError("invalid history language mode")
            try:
                terms = json.loads(row["normalized_terms_json"])
            except (TypeError, json.JSONDecodeError) as error:
                raise ValueError("invalid normalized history terms") from error
            if not isinstance(terms, list) or len(terms) > 30 or any(not isinstance(term, str) or len(term) > 300 for term in terms):
                raise ValueError("invalid normalized history terms")
        for row in normalized["user_profile"]:
            if row["id"] != 1:
                raise ValueError("invalid profile id")
            for key, limit in (("display_name", 100), ("role", 120), ("institution", 200), ("research_interests", 1000)):
                if not isinstance(row[key], str) or len(row[key]) > limit:
                    raise ValueError(f"invalid profile field: {key}")
        for row in normalized["notes"]:
            if not isinstance(row["title"], str) or len(row["title"]) > 300:
                raise ValueError("invalid note title")
            if not isinstance(row["content"], str) or len(row["content"]) > 500000:
                raise ValueError("invalid note content")
        seen_draw_ids: set[int] = set()
        for row in normalized["paper_draw_history"]:
            if not isinstance(row["id"], int) or row["id"] <= 0 or row["id"] in seen_draw_ids:
                raise ValueError("invalid draw history id")
            seen_draw_ids.add(row["id"])
            if not isinstance(row["query"], str) or not row["query"].strip() or len(row["query"]) > 300:
                raise ValueError("invalid draw query")
            if not isinstance(row["reason"], str) or len(row["reason"]) > 2000:
                raise ValueError("invalid draw reason")

        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM reading_tasks")
                conn.execute("DELETE FROM notes")
                conn.execute("DELETE FROM favorites")
                conn.execute("DELETE FROM search_history")
                conn.execute("DELETE FROM paper_draw_history")
                conn.execute("DELETE FROM reading_list")
                conn.execute("DELETE FROM user_profile")

                insert_sql = {
                    "reading_list": "INSERT INTO reading_list (paper_id, paper_json, status, priority, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    "reading_tasks": "INSERT INTO reading_tasks (id, paper_id, task_type, task_text, scheduled_date, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    "favorites": "INSERT INTO favorites (paper_id, paper_json, created_at) VALUES (?, ?, ?)",
                    "search_history": "INSERT INTO search_history (id, query, effective_query, query_language, language_mode, normalized_terms_json, result_count, seed_title, search_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    "user_profile": "INSERT INTO user_profile (id, display_name, role, institution, research_interests, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    "notes": "INSERT INTO notes (paper_id, paper_json, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    "paper_draw_history": "INSERT INTO paper_draw_history (id, query, paper_id, paper_json, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                }
                for table in ("reading_list", "reading_tasks", "favorites", "search_history", "user_profile", "notes", "paper_draw_history"):
                    columns = allowed_columns[table]
                    for row in normalized[table]:
                        conn.execute(insert_sql[table], tuple(row[column] for column in columns))
                conn.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {table: len(rows) for table, rows in normalized.items()}

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

    @staticmethod
    def _row_to_reading_task(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "paper": json.loads(row["paper_json"]),
            "task_type": row["task_type"],
            "task_text": row["task_text"],
            "scheduled_date": row["scheduled_date"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_draw(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "query": row["query"],
            "paper": json.loads(row["paper_json"]),
            "reason": row["reason"],
            "created_at": row["created_at"],
        }
