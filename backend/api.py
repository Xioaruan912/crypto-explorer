import logging
import os
import time
import uuid
import json
import hmac
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import requests

from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Use relative or local imports since the backend is now at the root of 'backend/'
from core.models import ResearchGraph
from fetchers.semantic_scholar import SemanticScholarClient
from fetchers.openalex import OpenAlexClient
from analyzer.graph_builder import GraphBuilder
from analyzer.heuristic_engine import HeuristicEngine
from core.logging_config import configure_logging
from core.research_store import ResearchStore

configure_logging()
logger = logging.getLogger("crypto_explorer.api")

enable_api_docs = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Crypto Explorer API",
    version="1.0.0",
    docs_url="/docs" if enable_api_docs else None,
    redoc_url="/redoc" if enable_api_docs else None,
    openapi_url="/openapi.json" if enable_api_docs else None,
)

SESSION_COOKIE = "crypto_session"
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(6 * 1024 * 1024)))

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

s2_client = SemanticScholarClient(api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
builder = GraphBuilder(s2_client)
openalex_client = OpenAlexClient()
openalex_builder = GraphBuilder(openalex_client)
engine = HeuristicEngine()

CACHE_DIR = Path(__file__).resolve().parent / "output"
store = ResearchStore(os.getenv("RESEARCH_DB_PATH", "/app/data/research.db"))


class ReadingListCreate(BaseModel):
    paper: dict
    status: str = "to_read"
    priority: int = Field(default=2, ge=1, le=3)
    note: str = Field(default="", max_length=4000)


class ReadingListUpdate(BaseModel):
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=3)
    note: str | None = Field(default=None, max_length=4000)


class FavoriteCreate(BaseModel):
    paper: dict


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=120)
    institution: str | None = Field(default=None, max_length=200)
    research_interests: str | None = Field(default=None, max_length=1000)


class NoteUpsert(BaseModel):
    paper: dict
    title: str = Field(default="", max_length=300)
    content: str = Field(default="", max_length=500000)


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class CredentialUpdate(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    username: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    new_password: str | None = Field(default=None, min_length=8, max_length=200)


class BackupImport(BaseModel):
    backup: dict[str, Any]


class ReadingTaskCreate(BaseModel):
    paper_id: str = Field(min_length=1, max_length=300)
    scheduled_date: str = Field(min_length=10, max_length=10)
    task_type: str = Field(default="read", max_length=30)
    task_text: str = Field(default="阅读论文", min_length=1, max_length=500)
    status: str = Field(default="todo", max_length=20)


class ReadingTaskUpdate(BaseModel):
    scheduled_date: str | None = Field(default=None, min_length=10, max_length=10)
    task_type: str | None = Field(default=None, max_length=30)
    task_text: str | None = Field(default=None, min_length=1, max_length=500)
    status: str | None = Field(default=None, max_length=20)


READING_TASK_TYPES = {"read", "notes", "review", "reproduce", "custom"}
READING_TASK_STATUSES = {"todo", "doing", "done"}


def _session_payload(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    return store.get_session(token)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=COOKIE_SECURE, samesite="strict")


def _apply_security_headers(response: Response, path: str) -> Response:
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "no-referrer"
    response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["content-security-policy"] = (
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if path.startswith("/api/"):
        response.headers["cache-control"] = "no-store"
    return response


def _validate_iso_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="date must use YYYY-MM-DD") from error
    return value


def _validate_reading_task_fields(values: dict) -> None:
    if values.get("scheduled_date") is not None:
        _validate_iso_date(values["scheduled_date"])
    if values.get("task_type") is not None and values["task_type"] not in READING_TASK_TYPES:
        raise HTTPException(status_code=422, detail="invalid reading task type")
    if values.get("status") is not None and values["status"] not in READING_TASK_STATUSES:
        raise HTTPException(status_code=422, detail="invalid reading task status")


def _load_cached_graph(query: str, max_nodes: int) -> ResearchGraph | None:
    normalized = " ".join(query.lower().replace("-", " ").split())
    if "registration based encryption" not in normalized:
        return None

    cache_path = CACHE_DIR / "Registration-Based_Encryption_Garg_data.json"
    if not cache_path.exists():
        return None

    try:
        graph = ResearchGraph.model_validate(json.loads(cache_path.read_text(encoding="utf-8")))
        descendants = [
            node
            for paper_id, node in graph.nodes.items()
            if paper_id != graph.seed_paper_id
        ]
        descendants.sort(key=lambda node: node.paper.citationCount, reverse=True)
        keep_ids = {graph.seed_paper_id}
        keep_ids.update(node.paper.paperId for node in descendants[:max_nodes])

        graph.nodes = {
            paper_id: node
            for paper_id, node in graph.nodes.items()
            if paper_id in keep_ids
        }
        for node in graph.nodes.values():
            node.citations = [paper_id for paper_id in node.citations if paper_id in keep_ids]
            node.cited_by = [paper_id for paper_id in node.cited_by if paper_id in keep_ids]
            node.in_degree_subgraph = len(node.cited_by)

        graph.taxonomy = {
            category: [paper_id for paper_id in paper_ids if paper_id in keep_ids]
            for category, paper_ids in graph.taxonomy.items()
            if any(paper_id in keep_ids for paper_id in paper_ids)
        }
        return graph
    except Exception:
        logger.exception("failed to load cached graph path=%s", cache_path)
        return None


def _build_openalex_fallback(query: str, max_nodes: int) -> ResearchGraph:
    logger.warning("search falling back provider=openalex query=%r", query)
    graph = openalex_builder.build_graph(query, max_nodes=max_nodes)
    engine.apply_heuristics(graph)
    logger.info(
        "fallback search completed provider=openalex query=%r nodes=%s categories=%s",
        query,
        len(graph.nodes),
        len(graph.taxonomy),
    )
    return graph


def _filter_graph_years(graph: ResearchGraph, from_year: int | None, to_year: int | None) -> ResearchGraph:
    if from_year is None and to_year is None:
        return graph
    keep_ids = {
        paper_id
        for paper_id, node in graph.nodes.items()
        if node.paper.year is not None
        and (from_year is None or node.paper.year >= from_year)
        and (to_year is None or node.paper.year <= to_year)
    }
    keep_ids.add(graph.seed_paper_id)
    graph.nodes = {paper_id: node for paper_id, node in graph.nodes.items() if paper_id in keep_ids}
    for node in graph.nodes.values():
        node.citations = [paper_id for paper_id in node.citations if paper_id in keep_ids]
        node.cited_by = [paper_id for paper_id in node.cited_by if paper_id in keep_ids]
        node.in_degree_subgraph = len(node.cited_by)
    graph.taxonomy = {
        category: [paper_id for paper_id in paper_ids if paper_id in keep_ids]
        for category, paper_ids in graph.taxonomy.items()
        if any(paper_id in keep_ids for paper_id in paper_ids)
    }
    return graph


def _build_scoped_openalex_graph(
    query: str,
    max_nodes: int,
    from_year: int | None,
    to_year: int | None,
    strategy: str,
) -> ResearchGraph:
    seeds = openalex_client.search_works(
        query,
        limit=100 if strategy == "foundational" else 10,
        from_year=from_year,
        to_year=to_year,
        sort="foundational" if strategy == "foundational" else "relevance",
    )
    if not seeds:
        raise ValueError(f"No papers found for query: {query}")
    graph = openalex_builder.build_graph_from_seed(seeds[0], max_nodes=max_nodes)
    engine.apply_heuristics(graph)
    return _filter_graph_years(graph, from_year, to_year)


def _record_and_dump_graph(query: str, graph: ResearchGraph) -> dict:
    seed_title = ""
    seed_node = graph.nodes.get(graph.seed_paper_id)
    if seed_node is not None:
        seed_title = seed_node.paper.title
    try:
        store.add_search_history(query, len(graph.nodes), seed_title)
    except Exception:
        logger.exception("failed to persist search history query=%r", query)
    return graph.model_dump()


def _record_discovery_history(query: str, items: list[dict], search_type: str) -> None:
    seed_title = ""
    if items:
        first = items[0]
        seed_title = str(first.get("title") or first.get("name") or "")
    try:
        store.add_search_history(query, len(items), seed_title, search_type=search_type)
    except Exception:
        logger.exception(
            "failed to persist discovery history query=%r search_type=%s",
            query,
            search_type,
        )


def _discovery_provider_error(operation: str, error: Exception) -> HTTPException:
    logger.exception("openalex discovery failed operation=%s", operation)
    if isinstance(error, requests.HTTPError) and error.response is not None:
        if error.response.status_code == 429 or error.response.status_code >= 500:
            return HTTPException(status_code=503, detail="OpenAlex is temporarily unavailable. Please try again later.")
    return HTTPException(status_code=502, detail="Unable to load research discovery data.")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:8]
    started = time.perf_counter()

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return _apply_security_headers(
                    JSONResponse(status_code=413, content={"detail": "request body too large"}),
                    request.url.path,
                )
        except ValueError:
            return _apply_security_headers(
                JSONResponse(status_code=400, content={"detail": "invalid content length"}),
                request.url.path,
            )

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES:
            return _apply_security_headers(
                JSONResponse(status_code=413, content={"detail": "request body too large"}),
                request.url.path,
            )

    path = request.url.path
    public_paths = {"/", "/health", "/api/auth/login", "/api/auth/session"}
    if path.startswith("/api/") and path not in public_paths:
        session = _session_payload(request)
        if session is None:
            return _apply_security_headers(
                JSONResponse(status_code=401, content={"detail": "authentication required"}),
                path,
            )
        if session.get("must_change_password") and path not in {"/api/auth/credentials", "/api/auth/logout"}:
            return _apply_security_headers(
                JSONResponse(status_code=428, content={"detail": "password change required"}),
                path,
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            csrf = request.headers.get("x-csrf-token", "")
            if not csrf or not hmac.compare_digest(csrf, str(session.get("csrf_token", ""))):
                return _apply_security_headers(
                    JSONResponse(status_code=403, content={"detail": "invalid csrf token"}),
                    path,
                )

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "request failed request_id=%s method=%s path=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["x-request-id"] = request_id
    _apply_security_headers(response, path)
    logger.info(
        "request request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.post("/api/auth/login")
def login(payload: LoginPayload, response: Response):
    status, user = store.authenticate(payload.username.strip(), payload.password)
    if status == "locked":
        raise HTTPException(status_code=429, detail="too many login attempts; try again later")
    if status != "ok" or user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    store.delete_all_sessions()
    token, session = store.create_session(SESSION_TTL_HOURS)
    _set_session_cookie(response, token)
    logger.info("account login username=%s", user["username"])
    return {
        "authenticated": True,
        "username": user["username"],
        "must_change_password": user["must_change_password"],
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
    }


@app.get("/api/auth/session")
def auth_session(request: Request):
    session = _session_payload(request)
    if session is None:
        account = store.get_account()
        return {
            "authenticated": False,
            "default_credentials_active": bool(account["must_change_password"]),
        }
    return {
        "authenticated": True,
        "username": session["username"],
        "must_change_password": session["must_change_password"],
        "default_credentials_active": False,
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    store.delete_session(request.cookies.get(SESSION_COOKIE, ""))
    _clear_session_cookie(response)
    return {"status": "logged_out"}


@app.get("/api/auth/account")
def get_account():
    return store.get_account()


@app.patch("/api/auth/credentials")
def update_credentials(payload: CredentialUpdate, request: Request, response: Response):
    username = payload.username.strip() if payload.username is not None else None
    if payload.new_password and payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="new password must be different")
    account = store.update_credentials(payload.current_password, username, payload.new_password)
    if account is None:
        raise HTTPException(status_code=401, detail="current password is incorrect")
    store.delete_all_sessions()
    token, session = store.create_session(SESSION_TTL_HOURS)
    _set_session_cookie(response, token)
    logger.info("account credentials updated username=%s", account["username"])
    return {
        **account,
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
    }


@app.get("/api/backup/export")
def export_backup():
    backup = store.export_backup()
    return JSONResponse(
        content=backup,
        headers={"Content-Disposition": f'attachment; filename="crypto-explorer-backup-{date.today().isoformat()}.json"'},
    )


@app.post("/api/backup/import")
def import_backup(payload: BackupImport):
    serialized_size = len(json.dumps(payload.backup, ensure_ascii=False).encode("utf-8"))
    if serialized_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="backup file too large")
    try:
        counts = store.import_backup(payload.backup)
    except (ValueError, json.JSONDecodeError, sqlite3.IntegrityError) as error:
        logger.warning("backup import rejected error=%s", type(error).__name__)
        raise HTTPException(status_code=422, detail="invalid backup file") from error
    logger.info("backup import completed counts=%s", counts)
    return {"status": "restored", "counts": counts}

@app.get("/")
def read_root():
    return {"status": "ok", "service": "crypto-explorer-api", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/reading-list")
def get_reading_list():
    return {"items": store.list_reading()}


@app.post("/api/reading-list")
def add_reading_list(payload: ReadingListCreate):
    paper_id = str(payload.paper.get("id", "")).strip()
    if not paper_id:
        raise HTTPException(status_code=422, detail="paper.id is required")
    if payload.status not in {"to_read", "reading", "done"}:
        raise HTTPException(status_code=422, detail="invalid reading status")
    item = store.upsert_reading(payload.paper, payload.status, payload.priority, payload.note)
    logger.info("reading list upsert paper_id=%s status=%s priority=%s", paper_id, payload.status, payload.priority)
    return item


@app.patch("/api/reading-list/{paper_id}")
def update_reading_list(paper_id: str, payload: ReadingListUpdate):
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in {"to_read", "reading", "done"}:
        raise HTTPException(status_code=422, detail="invalid reading status")
    item = store.update_reading(paper_id, values)
    if item is None:
        raise HTTPException(status_code=404, detail="reading list item not found")
    logger.info("reading list update paper_id=%s fields=%s", paper_id, sorted(values.keys()))
    return item


@app.delete("/api/reading-list/{paper_id}")
def delete_reading_list(paper_id: str):
    if not store.delete_reading(paper_id):
        raise HTTPException(status_code=404, detail="reading list item not found")
    logger.info("reading list delete paper_id=%s", paper_id)
    return {"status": "deleted"}


@app.get("/api/reading-tasks")
def get_reading_tasks(
    from_date: str = Query(min_length=10, max_length=10),
    to_date: str = Query(min_length=10, max_length=10),
):
    start = _validate_iso_date(from_date)
    end = _validate_iso_date(to_date)
    if start > end:
        raise HTTPException(status_code=422, detail="from_date must not be after to_date")
    return {"items": store.list_reading_tasks(start, end)}


@app.post("/api/reading-tasks")
def create_reading_task(payload: ReadingTaskCreate):
    values = payload.model_dump()
    _validate_reading_task_fields(values)
    item = store.create_reading_task(**values)
    if item is None:
        raise HTTPException(status_code=404, detail="reading list item not found")
    logger.info(
        "reading task create task_id=%s paper_id=%s date=%s type=%s",
        item["id"],
        payload.paper_id,
        payload.scheduled_date,
        payload.task_type,
    )
    return item


@app.patch("/api/reading-tasks/{task_id}")
def update_reading_task(task_id: int, payload: ReadingTaskUpdate):
    values = payload.model_dump(exclude_unset=True)
    _validate_reading_task_fields(values)
    item = store.update_reading_task(task_id, values)
    if item is None:
        raise HTTPException(status_code=404, detail="reading task not found")
    logger.info("reading task update task_id=%s fields=%s", task_id, sorted(values.keys()))
    return item


@app.delete("/api/reading-tasks/{task_id}")
def delete_reading_task(task_id: int):
    if not store.delete_reading_task(task_id):
        raise HTTPException(status_code=404, detail="reading task not found")
    logger.info("reading task delete task_id=%s", task_id)
    return {"status": "deleted"}


@app.get("/api/favorites")
def get_favorites():
    return {"items": store.list_favorites()}


@app.post("/api/favorites")
def add_favorite(payload: FavoriteCreate):
    paper_id = str(payload.paper.get("id", "")).strip()
    if not paper_id:
        raise HTTPException(status_code=422, detail="paper.id is required")
    item = store.upsert_favorite(payload.paper)
    logger.info("favorite upsert paper_id=%s", paper_id)
    return item


@app.delete("/api/favorites/{paper_id}")
def delete_favorite(paper_id: str):
    if not store.delete_favorite(paper_id):
        raise HTTPException(status_code=404, detail="favorite not found")
    logger.info("favorite delete paper_id=%s", paper_id)
    return {"status": "deleted"}


@app.get("/api/history")
def get_history(limit: int = Query(default=100, ge=1, le=500)):
    return {"items": store.list_search_history(limit)}


@app.delete("/api/history/{history_id}")
def delete_history(history_id: int):
    if not store.delete_search_history(history_id):
        raise HTTPException(status_code=404, detail="history item not found")
    return {"status": "deleted"}


@app.delete("/api/history")
def clear_history():
    deleted = store.clear_search_history()
    logger.info("history cleared count=%s", deleted)
    return {"status": "deleted", "count": deleted}


@app.get("/api/profile")
def get_profile():
    return store.get_profile()


@app.patch("/api/profile")
def update_profile(payload: ProfileUpdate):
    profile = store.update_profile(payload.model_dump(exclude_unset=True))
    logger.info("profile updated")
    return profile


@app.get("/api/dashboard")
def get_dashboard():
    return store.dashboard()


@app.get("/api/notes")
def get_notes():
    return {"items": store.list_notes()}


@app.get("/api/notes/{paper_id}")
def get_note(paper_id: str):
    note = store.get_note(paper_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@app.put("/api/notes/{paper_id}")
def save_note(paper_id: str, payload: NoteUpsert):
    body_id = str(payload.paper.get("id", "")).strip()
    if not body_id or body_id != paper_id:
        raise HTTPException(status_code=422, detail="paper.id must match path")
    return store.upsert_note(payload.paper, payload.title, payload.content)


@app.delete("/api/notes/{paper_id}")
def delete_note(paper_id: str):
    if not store.delete_note(paper_id):
        raise HTTPException(status_code=404, detail="note not found")
    return {"status": "deleted"}


@app.get("/api/discovery/papers")
def discover_papers(
    query: str = Query(min_length=2, max_length=300),
    from_year: int | None = Query(default=None, ge=1900, le=2100),
    to_year: int | None = Query(default=None, ge=1900, le=2100),
    author: str | None = Query(default=None, max_length=120),
    venue: str | None = Query(default=None, max_length=160),
    sort: str = Query(default="relevance", pattern="^(relevance|citations|newest)$"),
    open_access: bool = False,
    limit: int = Query(default=25, ge=1, le=50),
):
    normalized_query = query.strip()
    if from_year and to_year and from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year cannot be greater than to_year")
    try:
        fetch_limit = 100 if author or venue else limit
        items = openalex_client.search_works(
            normalized_query,
            limit=fetch_limit,
            from_year=from_year,
            to_year=to_year,
            sort=sort,
            open_access_only=open_access,
        )
        if author:
            needle = author.strip().casefold()
            items = [
                item
                for item in items
                if any(needle in str(person.get("name", "")).casefold() for person in item.get("authors") or [])
            ]
        if venue:
            venue_needle = venue.strip().casefold()
            items = [
                item
                for item in items
                if venue_needle in str(item.get("venue") or "").casefold()
            ]
        items = items[:limit]
        _record_discovery_history(normalized_query, items, "papers")
        logger.info("paper discovery completed query=%r results=%s", normalized_query, len(items))
        return {"items": items, "count": len(items), "provider": "OpenAlex"}
    except HTTPException:
        raise
    except Exception as error:
        raise _discovery_provider_error("papers", error) from error


@app.get("/api/discovery/authors")
def discover_authors(
    query: str = Query(min_length=2, max_length=200),
    sort: str = Query(default="relevance", pattern="^(relevance|citations|works)$"),
    limit: int = Query(default=20, ge=1, le=50),
):
    normalized_query = query.strip()
    try:
        items = openalex_client.search_authors(normalized_query, limit=limit, sort=sort)
        _record_discovery_history(normalized_query, items, "authors")
        logger.info("author discovery completed query=%r results=%s", normalized_query, len(items))
        return {"items": items, "count": len(items), "provider": "OpenAlex"}
    except Exception as error:
        raise _discovery_provider_error("authors", error) from error


@app.get("/api/discovery/authors/{author_id}")
def author_detail(
    author_id: str = ApiPath(pattern=r"^A\d+$"),
    works_limit: int = Query(default=12, ge=1, le=30),
):
    try:
        return openalex_client.get_author(author_id, works_limit=works_limit)
    except Exception as error:
        raise _discovery_provider_error("author-detail", error) from error


@app.get("/api/discovery/venues")
def discover_venues(
    query: str = Query(min_length=2, max_length=200),
    sort: str = Query(default="relevance", pattern="^(relevance|citations|works)$"),
    limit: int = Query(default=20, ge=1, le=50),
):
    normalized_query = query.strip()
    try:
        items = openalex_client.search_sources(normalized_query, limit=limit, sort=sort)
        _record_discovery_history(normalized_query, items, "venues")
        logger.info("venue discovery completed query=%r results=%s", normalized_query, len(items))
        return {"items": items, "count": len(items), "provider": "OpenAlex"}
    except Exception as error:
        raise _discovery_provider_error("venues", error) from error


@app.get("/api/discovery/venues/{source_id}")
def venue_detail(
    source_id: str = ApiPath(pattern=r"^S\d+$"),
    works_limit: int = Query(default=12, ge=1, le=30),
):
    try:
        return openalex_client.get_source(source_id, works_limit=works_limit)
    except Exception as error:
        raise _discovery_provider_error("venue-detail", error) from error

@app.get("/api/search")
def search_topic(
    query: str = Query(min_length=2, max_length=300),
    max_nodes: int = Query(default=20, ge=1, le=50),
    from_year: int | None = Query(default=None, ge=1800, le=2100),
    to_year: int | None = Query(default=None, ge=1800, le=2100),
    strategy: str = Query(default="relevance", pattern="^(relevance|foundational)$"),
):
    normalized_query = query.strip()
    if from_year and to_year and from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year must be <= to_year")
    logger.info("search started query=%r max_nodes=%s", normalized_query, max_nodes)
    if from_year is not None or to_year is not None or strategy == "foundational":
        try:
            graph = _build_scoped_openalex_graph(
                normalized_query,
                max_nodes=max_nodes,
                from_year=from_year,
                to_year=to_year,
                strategy=strategy,
            )
            logger.info(
                "scoped search completed query=%r strategy=%s from_year=%s to_year=%s nodes=%s",
                normalized_query,
                strategy,
                from_year,
                to_year,
                len(graph.nodes),
            )
            return _record_and_dump_graph(normalized_query, graph)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except requests.RequestException as e:
            logger.exception("scoped openalex search failed query=%r", normalized_query)
            raise HTTPException(status_code=503, detail="Research provider is temporarily unavailable") from e
    try:
        graph = builder.build_graph(normalized_query, max_nodes=max_nodes)
        engine.apply_heuristics(graph)
        logger.info(
            "search completed query=%r nodes=%s categories=%s",
            normalized_query,
            len(graph.nodes),
            len(graph.taxonomy),
        )
        return _record_and_dump_graph(normalized_query, graph)
    except ValueError as e:
        logger.warning("search returned no result query=%r error=%s", normalized_query, e)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        cached_graph = _load_cached_graph(normalized_query, max_nodes) if status_code == 429 else None
        if cached_graph is not None:
            logger.warning(
                "search provider rate limited; serving cached graph query=%r nodes=%s",
                normalized_query,
                len(cached_graph.nodes),
            )
            return _record_and_dump_graph(normalized_query, cached_graph)
        if status_code == 429 or (status_code is not None and status_code >= 500):
            try:
                return _record_and_dump_graph(
                    normalized_query,
                    _build_openalex_fallback(normalized_query, max_nodes),
                )
            except Exception as fallback_error:
                logger.exception("openalex fallback failed query=%r", normalized_query)
                raise HTTPException(
                    status_code=503,
                    detail="Research providers are temporarily unavailable. Please try again later.",
                ) from fallback_error
        logger.exception("search provider http error query=%r", normalized_query)
        raise HTTPException(status_code=502, detail="Research provider request failed") from e
    except requests.RequestException as e:
        logger.warning("semantic scholar network error; trying openalex query=%r error=%s", normalized_query, e)
        try:
            return _record_and_dump_graph(
                normalized_query,
                _build_openalex_fallback(normalized_query, max_nodes),
            )
        except Exception as fallback_error:
            logger.exception("openalex fallback failed query=%r", normalized_query)
            raise HTTPException(
                status_code=503,
                detail="Research providers are temporarily unavailable. Please try again later.",
            ) from fallback_error
    except Exception as e:
        logger.exception("search provider failed query=%r", normalized_query)
        raise HTTPException(status_code=502, detail="Research provider request failed") from e
