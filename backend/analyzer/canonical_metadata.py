from __future__ import annotations

import html
import logging
import os
import re
import threading
import time
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote

import requests

from core.research_store import ResearchStore
from fetchers.openalex import OpenAlexClient


logger = logging.getLogger("crypto_explorer.canonical_metadata")
DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
CROSSREF_BASE_URL = "https://api.crossref.org"
CANONICAL_CACHE_VERSION = 2


def _plain(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", text).strip()


def _title_key(value: str) -> str:
    value = re.sub(r"\(\s*reprint\s*\)", "", value, flags=re.I)
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _surname(value: str) -> str:
    parts = re.findall(r"[a-z]+", value.casefold())
    return parts[-1] if parts else ""


def _title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _title_key(left), _title_key(right)).ratio()


def _year_from_parts(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list) or not parts[0]:
        return None
    try:
        year = int(parts[0][0])
    except (TypeError, ValueError):
        return None
    return year if 1800 <= year <= 2200 else None


def _year_from_venue_text(value: str) -> int | None:
    text = html.unescape(value)
    full = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if full:
        return int(full.group(1))
    short = re.search(r"(?:['’`]|\b)(\d{2})\b", text)
    if short:
        year = int(short.group(1))
        return 1900 + year if year >= 40 else 2000 + year
    return None


class CanonicalMetadataResolver:
    """Normalize reprints/electronic editions to the original bibliographic record.

    DBLP is preferred for computer-science conference/journal history. Crossref is
    used as an independent DOI/bibliographic fallback. The original OpenAlex values
    are retained in `sourceYear/sourceVenue/sourceDoi` for transparency.
    """

    def __init__(self, store: ResearchStore, openalex: OpenAlexClient | None = None) -> None:
        self.store = store
        self.openalex = openalex
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CryptoExplorer/1.0 canonical metadata resolver"})
        self.crossref_mailto = os.getenv("CROSSREF_MAILTO", os.getenv("OPENALEX_MAILTO", "")).strip()
        self._request_lock = threading.Lock()
        self._last_request_at = 0.0
        self._blocked_until: dict[str, float] = {}

    def canonicalize(self, work: dict[str, Any]) -> dict[str, Any]:
        title = str(work.get("title") or "").strip()
        if not title:
            return work
        first_author = ""
        authors = work.get("authors") or []
        if authors:
            first = authors[0]
            first_author = str(first.get("name") if isinstance(first, dict) else first or "")
        cache_key = f"v{CANONICAL_CACHE_VERSION}|{_title_key(title)}|{_surname(first_author)}"
        cached = self.store.get_canonical_metadata_cache(cache_key)
        if cached is not None:
            return self._apply(work, cached)

        source = {
            "year": work.get("year"),
            "venue": work.get("venue"),
            "doi": ((work.get("externalIds") or {}).get("DOI") if isinstance(work.get("externalIds"), dict) else None),
        }
        candidates: list[dict[str, Any]] = []
        dblp_candidates: list[dict[str, Any]] = []
        if self._provider_available("dblp"):
            try:
                dblp_candidates = self._dblp_candidates(title, first_author)
                candidates.extend(dblp_candidates)
            except requests.RequestException as error:
                self._cooldown_provider("dblp", error)
                logger.warning("DBLP metadata lookup unavailable title=%r error=%s", title, type(error).__name__)
        dblp_best = self._choose(title, first_author, dblp_candidates)
        # An exact DBLP title+author match is strong enough for CS bibliography and
        # avoids a second provider request for every milestone.
        if not (dblp_best and dblp_best.get("exact") and dblp_best.get("authorMatch")) and self._provider_available("crossref"):
            try:
                candidates.extend(self._crossref_candidates(title, first_author, source.get("doi")))
            except requests.RequestException as error:
                self._cooldown_provider("crossref", error)
                logger.warning("Crossref metadata lookup unavailable title=%r error=%s", title, type(error).__name__)

        chosen = self._choose(title, first_author, candidates)
        if chosen is None and self.openalex is not None:
            try:
                chosen = self._choose(title, first_author, self._openalex_candidates(title, first_author))
            except (requests.RequestException, ValueError):
                logger.warning("OpenAlex duplicate metadata fallback unavailable title=%r", title)
        canonical = {
            "canonicalYear": chosen.get("year") if chosen else source.get("year"),
            "canonicalVenue": chosen.get("venue") if chosen else source.get("venue"),
            "canonicalDoi": chosen.get("doi") if chosen else source.get("doi"),
            "canonicalSource": chosen.get("source") if chosen else "OpenAlex",
            "canonicalConfidence": chosen.get("confidence") if chosen else "source",
            "dblpUrl": chosen.get("dblpUrl") if chosen else None,
            "isReprintLike": bool(
                chosen
                and chosen.get("source") == "OpenAlex duplicate resolution"
                and source.get("year")
                and chosen.get("year")
                and int(chosen["year"]) <= int(source["year"]) - 3
            ),
        }
        self.store.upsert_canonical_metadata_cache(cache_key, canonical)
        return self._apply(work, canonical)

    def canonicalize_many(self, works: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for index, work in enumerate(works):
            if index < limit:
                result.append(self.canonicalize(work))
            else:
                result.append(work)
        return result

    def _provider_available(self, provider: str) -> bool:
        return time.monotonic() >= self._blocked_until.get(provider, 0.0)

    def _cooldown_provider(self, provider: str, error: requests.RequestException) -> None:
        seconds = 60.0
        response = getattr(error, "response", None)
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            try:
                seconds = max(120.0, min(float(retry_after), 900.0)) if retry_after else 300.0
            except (TypeError, ValueError):
                seconds = 300.0
        self._blocked_until[provider] = time.monotonic() + seconds

    def _paced_get(self, url: str, **kwargs: Any) -> requests.Response:
        with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < 0.35:
                time.sleep(0.35 - elapsed)
            response = self.session.get(url, timeout=6, **kwargs)
            self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response

    def _openalex_candidates(self, title: str, first_author: str) -> list[dict[str, Any]]:
        if self.openalex is None:
            return []
        works = self.openalex.search_works(title, limit=8, sort="foundational")
        candidates: list[dict[str, Any]] = []
        for work in works:
            candidate_title = str(work.get("title") or "")
            if candidate_title.casefold().startswith("withdrawn:"):
                continue
            similarity = _title_similarity(title, candidate_title)
            if similarity < 0.90:
                continue
            authors = [
                str(author.get("name") or "")
                for author in (work.get("authors") or [])
                if isinstance(author, dict)
            ]
            author_match = not first_author or any(_surname(first_author) == _surname(author) for author in authors)
            if first_author and not author_match and similarity < 0.98:
                continue
            candidates.append(
                {
                    "title": candidate_title,
                    "year": work.get("year"),
                    "venue": work.get("venue"),
                    "doi": ((work.get("externalIds") or {}).get("DOI") if isinstance(work.get("externalIds"), dict) else None),
                    "source": "OpenAlex duplicate resolution",
                    "similarity": similarity,
                    "authorMatch": author_match,
                }
            )
        return candidates

    def _dblp_candidates(self, title: str, first_author: str) -> list[dict[str, Any]]:
        response = self._paced_get(
            DBLP_SEARCH_URL,
            params={"q": title, "format": "json", "h": 8},
        )
        hits = response.json().get("result", {}).get("hits", {}).get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]
        candidates: list[dict[str, Any]] = []
        for hit in hits if isinstance(hits, list) else []:
            info = hit.get("info") or {}
            candidate_title = _plain(info.get("title"))
            if not candidate_title:
                continue
            similarity = _title_similarity(title, candidate_title)
            if similarity < 0.80:
                continue
            authors = self._dblp_authors(info.get("authors"))
            author_match = not first_author or any(_surname(first_author) == _surname(author) for author in authors)
            if first_author and not author_match and similarity < 0.96:
                continue
            try:
                year = int(info.get("year")) if info.get("year") else None
            except (TypeError, ValueError):
                year = None
            candidates.append(
                {
                    "title": candidate_title,
                    "year": year,
                    "venue": _plain(info.get("venue")),
                    "doi": _plain(info.get("doi")) or None,
                    "dblpUrl": _plain(info.get("url")) or None,
                    "source": "DBLP",
                    "similarity": similarity,
                    "authorMatch": author_match,
                }
            )
        return candidates

    @staticmethod
    def _dblp_authors(value: Any) -> list[str]:
        if not isinstance(value, dict):
            return []
        author = value.get("author")
        if isinstance(author, str):
            return [_plain(author)]
        if isinstance(author, dict):
            return [_plain(author.get("text") or author.get("@pid") or "")]
        if isinstance(author, list):
            result: list[str] = []
            for item in author:
                if isinstance(item, str):
                    result.append(_plain(item))
                elif isinstance(item, dict):
                    result.append(_plain(item.get("text") or ""))
            return [item for item in result if item]
        return []

    def _crossref_candidates(self, title: str, first_author: str, doi: Any) -> list[dict[str, Any]]:
        params = {"rows": 5, "query.bibliographic": f"{title} {first_author}".strip()}
        if self.crossref_mailto:
            params["mailto"] = self.crossref_mailto
        response = self._paced_get(f"{CROSSREF_BASE_URL}/works", params=params)
        items = response.json().get("message", {}).get("items", [])
        candidates: list[dict[str, Any]] = []
        for item in items if isinstance(items, list) else []:
            titles = item.get("title") or []
            candidate_title = _plain(titles[0]) if isinstance(titles, list) and titles else ""
            if not candidate_title:
                continue
            similarity = _title_similarity(title, candidate_title)
            if similarity < 0.82:
                continue
            authors = [
                " ".join(filter(None, [str(author.get("given") or ""), str(author.get("family") or "")])).strip()
                for author in (item.get("author") or [])
                if isinstance(author, dict)
            ]
            author_match = not first_author or any(_surname(first_author) == _surname(author) for author in authors)
            if first_author and not author_match and similarity < 0.97:
                continue
            years = [
                _year_from_parts(item.get(key))
                for key in ("published-print", "issued", "published-online", "created")
            ]
            containers = item.get("container-title") or []
            venue_options = [_plain(value) for value in containers if value] if isinstance(containers, list) else []
            venue = next(
                (
                    value for value in venue_options
                    if re.search(r"crypto|eurocrypt|asiacrypt|symposium|conference|security", value, flags=re.I)
                ),
                venue_options[0] if venue_options else "",
            )
            venue_context = " ".join(venue_options)
            year_values = [year for year in years if year is not None]
            venue_year = _year_from_venue_text(venue_context)
            if venue_year is not None:
                year_values.append(venue_year)
            candidates.append(
                {
                    "title": candidate_title,
                    "year": min(year_values) if year_values else None,
                    "venue": venue,
                    "doi": _plain(item.get("DOI")) or None,
                    "source": "Crossref",
                    "similarity": similarity,
                    "authorMatch": author_match,
                }
            )
        return candidates

    @staticmethod
    def _choose(title: str, first_author: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        valid = [candidate for candidate in candidates if candidate.get("year") and candidate.get("similarity", 0) >= 0.84]
        if not valid:
            return None
        original_key = _title_key(title)
        for candidate in valid:
            exact = _title_key(str(candidate.get("title") or "")) == original_key
            candidate["exact"] = exact
            candidate["confidence"] = "high" if exact and candidate.get("authorMatch") else "medium"
        # For exact-title duplicates, the earliest matching record is normally the
        # original publication and later hits are reprints/electronic editions.
        return min(
            valid,
            key=lambda candidate: (
                0 if candidate.get("exact") else 1,
                0 if candidate.get("authorMatch") else 1,
                int(candidate.get("year") or 9999),
                0 if candidate.get("source") == "DBLP" else 1,
                -float(candidate.get("similarity") or 0),
            ),
        )

    @staticmethod
    def _apply(work: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
        result = dict(work)
        source_year = result.get("year")
        source_venue = result.get("venue")
        external_ids = dict(result.get("externalIds") or {})
        source_doi = external_ids.get("DOI")
        canonical_year = canonical.get("canonicalYear")
        canonical_venue = canonical.get("canonicalVenue")
        canonical_doi = canonical.get("canonicalDoi")
        if canonical_year:
            result["year"] = canonical_year
        if canonical_venue:
            result["venue"] = canonical_venue
        if canonical_doi:
            external_ids["DOI"] = canonical_doi
            result["externalIds"] = external_ids
        if canonical.get("dblpUrl"):
            result["dblpUrl"] = canonical["dblpUrl"]
        result["sourceYear"] = source_year
        result["sourceVenue"] = source_venue
        result["sourceDoi"] = source_doi
        result["canonicalSource"] = canonical.get("canonicalSource") or "OpenAlex"
        result["canonicalConfidence"] = canonical.get("canonicalConfidence") or "source"
        result["isReprintLike"] = bool(canonical.get("isReprintLike"))
        return result
