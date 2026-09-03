"""Local security regression smoke test using only the Python standard library."""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def request(opener, base: str, path: str, method: str = "GET", body=None, csrf: str | None = None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    if csrf:
        headers["x-csrf-token"] = csrf
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def wait_for_server(base: str) -> None:
    opener = urllib.request.build_opener()
    for _ in range(50):
        try:
            status, _ = request(opener, base, "/health")
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("security smoke server did not start")


def main() -> int:
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="crypto-security-") as temp_dir:
        db_path = Path(temp_dir) / "research.db"
        port = 18083
        base = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env.update(
            {
                "RESEARCH_DB_PATH": str(db_path),
                "COOKIE_SECURE": "false",
                "ENABLE_API_DOCS": "false",
                "SESSION_TTL_HOURS": "720",
                "SESSION_RENEW_BEFORE_HOURS": "168",
            }
        )
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_for_server(base)
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

            status, _ = request(opener, base, "/api/dashboard")
            assert status == 401
            status, _ = request(opener, base, "/api/genealogy?query=test")
            assert status == 401
            status, _ = request(opener, base, "/api/paper-draw", "POST", {"query": "test"})
            assert status == 401
            status, _ = request(opener, base, "/docs")
            assert status == 404

            default_password = "123" + "456"
            status, login = request(
                opener,
                base,
                "/api/auth/login",
                "POST",
                {"username": "admin", "password": default_password},
            )
            assert status == 200 and login["must_change_password"] is True
            csrf = login["csrf_token"]
            login_cookie = next(cookie for cookie in jar if cookie.name == "crypto_session")
            first_cookie = login_cookie.value
            assert login_cookie.discard is False
            assert login_cookie.expires is not None
            assert login_cookie.expires - time.time() > 29 * 24 * 3600

            status, _ = request(opener, base, "/api/dashboard")
            assert status == 428
            generated_password = "T!" + secrets.token_urlsafe(18)
            status, _ = request(
                opener,
                base,
                "/api/auth/credentials",
                "PATCH",
                {"current_password": default_password, "new_password": generated_password},
            )
            assert status == 403
            status, changed = request(
                opener,
                base,
                "/api/auth/credentials",
                "PATCH",
                {"current_password": default_password, "new_password": generated_password},
                csrf,
            )
            assert status == 200 and changed["must_change_password"] is False
            csrf2 = changed["csrf_token"]
            second_cookie_obj = next(cookie for cookie in jar if cookie.name == "crypto_session")
            second_cookie = second_cookie_obj.value
            assert first_cookie != second_cookie
            assert second_cookie_obj.discard is False
            assert second_cookie_obj.expires is not None

            # A valid session close to expiry should be extended without forcing a new login.
            near_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "UPDATE auth_sessions SET expires_at = ? WHERE token_hash = ?",
                    (near_expiry, hashlib.sha256(second_cookie.encode()).hexdigest()),
                )
            status, renewed = request(opener, base, "/api/auth/session")
            assert status == 200 and renewed["authenticated"] is True
            with sqlite3.connect(db_path) as conn:
                renewed_expiry = conn.execute(
                    "SELECT expires_at FROM auth_sessions WHERE token_hash = ?",
                    (hashlib.sha256(second_cookie.encode()).hexdigest(),),
                ).fetchone()[0]
            assert datetime.fromisoformat(renewed_expiry) > datetime.now(timezone.utc) + timedelta(days=29)
            renewed_cookie = next(cookie for cookie in jar if cookie.name == "crypto_session")
            assert renewed_cookie.expires is not None
            assert renewed_cookie.expires - time.time() > 29 * 24 * 3600

            status, _ = request(opener, base, "/api/dashboard")
            assert status == 200
            status, draw_history = request(opener, base, "/api/paper-draw/history")
            assert status == 200 and draw_history["items"] == []
            status, _ = request(opener, base, "/api/history", "DELETE", csrf=csrf)
            assert status == 403

            status, backup = request(opener, base, "/api/backup/export")
            assert status == 200 and backup["format"] == "crypto-explorer-backup"
            backup_text = json.dumps(backup)
            for forbidden in ("password_hash", "auth_sessions", "csrf_token", "crypto_session"):
                assert forbidden not in backup_text

            status, _ = request(
                opener,
                base,
                "/api/backup/import",
                "POST",
                {"backup": {"format": "wrong", "version": 1, "tables": {}}},
                csrf2,
            )
            assert status == 422
            status, _ = request(opener, base, "/api/backup/import", "POST", {"backup": backup}, csrf2)
            assert status == 200

            with sqlite3.connect(db_path) as conn:
                stored_hash = conn.execute("SELECT password_hash FROM auth_user WHERE id = 1").fetchone()[0]
                stored_session_hash = conn.execute(
                    "SELECT token_hash FROM auth_sessions ORDER BY created_at DESC LIMIT 1"
                ).fetchone()[0]
            assert stored_hash.startswith("scrypt$")
            raw_db = db_path.read_bytes()
            assert generated_password.encode() not in raw_db
            assert stored_session_hash == hashlib.sha256(second_cookie.encode()).hexdigest()
            assert second_cookie.encode() not in raw_db

            for _ in range(5):
                status, _ = request(
                    opener,
                    base,
                    "/api/auth/login",
                    "POST",
                    {"username": "admin", "password": "incorrect-test-password"},
                )
                assert status == 401
            status, _ = request(
                opener,
                base,
                "/api/auth/login",
                "POST",
                {"username": "admin", "password": "incorrect-test-password"},
            )
            assert status == 429

            print("SECURITY_SMOKE=PASS")
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
