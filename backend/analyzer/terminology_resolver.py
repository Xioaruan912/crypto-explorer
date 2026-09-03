from __future__ import annotations

import csv
import io
import logging
import re
import threading
import time
import zipfile
from collections import Counter, defaultdict
from typing import Any

import requests

from analyzer.query_normalizer import FILLER_ZH, detect_query_language, normalize_query
from core.research_store import ResearchStore
from fetchers.openalex import OpenAlexClient


logger = logging.getLogger("crypto_explorer.terminology")

WIKIPEDIA_API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
NIST_GLOSSARY_BASE = "https://csrc.nist.gov/glossary/term"
CSO_CSV_ZIP = "https://cso.kmi.open.ac.uk/download/version-3.5/CSO.3.5.csv.zip"

CRYPTO_EVIDENCE = {
    "crypt", "cipher", "encryption", "signature", "security", "privacy", "secret",
    "side channel", "side-channel", "timing attack", "power analysis", "fault attack",
    "zero knowledge", "zero-knowledge", "multiparty", "multi-party", "oblivious",
    "commitment", "hash", "public key", "public-key", "authentication", "lattice",
    "post-quantum", "isogeny", "protocol", "key exchange", "key agreement",
}


def _compact(value: str) -> str:
    return re.sub(r"[\s\-_/·，。！？、：；（）()\[\]{}]+", "", value.casefold())


def _clean_zh_query(value: str) -> str:
    cleaned = value.strip()
    for filler in sorted(FILLER_ZH | {"的", "关于", "相关的", "方向", "领域"}, key=len, reverse=True):
        cleaned = cleaned.replace(filler, "")
    cleaned = re.sub(r"[\s，。！？、：；（）()\[\]{}]+", "", cleaned)
    return cleaned or value.strip()


def _normalize_topic(value: str) -> str:
    value = value.casefold().replace("%28", "(").replace("%29", ")")
    value = re.sub(r"[_\-]+", " ", value)
    return " ".join(re.findall(r"[a-z0-9+.#]+", value))


def _academic_term(value: str) -> str:
    value = " ".join(value.replace("_", " ").split()).strip()
    if not value:
        return value
    # Academic search works better with normalized lower-case concept names while
    # preserving common all-uppercase abbreviations.
    return value if value.isupper() and len(value) <= 8 else value.casefold()


class TerminologyResolver:
    """Resolve Chinese research terms without turning the application into a giant hard-coded dictionary.

    Resolution order:
      user/local SQLite -> bootstrap overrides -> Chinese Wikipedia/Wikidata bridge
      -> CSO/NIST/OpenAlex validation -> SQLite self-learning cache.
    """

    def __init__(self, store: ResearchStore, openalex: OpenAlexClient) -> None:
        self.store = store
        self.openalex = openalex
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CryptoExplorer/1.0 (academic terminology resolver)"})
        self._cso_lock = threading.Lock()
        self._cso_loaded_at = 0.0
        self._cso_topics: set[str] = set()
        self._cso_related: dict[str, set[str]] = defaultdict(set)

    def normalize(self, query: str, mode: str = "academic_en") -> dict[str, Any]:
        original = query.strip()
        base = normalize_query(original, mode)
        if mode == "original" or base["detectedLanguage"] == "en":
            return self._decorate(base, None)

        # User-confirmed/local mappings always win and are available offline.
        local = self.store.find_term_mapping(original)
        if local is None:
            cleaned = _clean_zh_query(original)
            if cleaned != original:
                local = self.store.find_term_mapping(cleaned)
        if local is not None:
            return self._mapping_result(original, mode, local, "local")

        # Keep a small set of deterministic bootstrap mappings for offline startup.
        # They are an override/fallback layer, not the vocabulary database.
        if base.get("translated"):
            mapping = self._mapping_from_base(original, base)
            try:
                saved = self.store.upsert_term_mapping(mapping)
            except Exception:
                logger.exception("failed to persist bootstrap terminology mapping term=%r", original)
                saved = mapping
            return self._mapping_result(original, mode, saved, "bootstrap")

        try:
            mapping = self._resolve_dynamic(original)
        except requests.RequestException:
            logger.warning("terminology providers unavailable term=%r", original, exc_info=True)
            mapping = None
        except Exception:
            logger.exception("terminology resolution failed term=%r", original)
            mapping = None

        if mapping is None or float(mapping.get("confidence") or 0) < 0.62:
            result = dict(base)
            result.update(
                {
                    "resolutionStatus": "unresolved",
                    "confidenceScore": float(mapping.get("confidence") or 0) if mapping else 0.0,
                    "sources": list(mapping.get("sources") or []) if mapping else [],
                    "termMappingId": None,
                    "userConfirmed": False,
                }
            )
            return result

        # Auto-learn only when two independent signals agree, or when confidence is very high.
        sources = set(mapping.get("sources") or [])
        should_cache = float(mapping.get("confidence") or 0) >= 0.82 and len(sources) >= 2
        saved = mapping
        if should_cache:
            saved = self.store.upsert_term_mapping(mapping)
        return self._mapping_result(original, mode, saved, "dynamic")

    def resolve_and_persist(self, query: str) -> dict[str, Any]:
        """Force a fresh online resolution for the terminology management screen."""
        normalized_query = query.strip()
        existing = self.store.find_term_mapping(normalized_query)
        if existing is not None and existing.get("user_confirmed"):
            return existing
        mapping = self._resolve_dynamic(normalized_query)
        if mapping is None or float(mapping.get("confidence") or 0) < 0.55:
            raise ValueError("Unable to resolve the term with enough academic evidence")
        return self.store.upsert_term_mapping(mapping)

    def _mapping_from_base(self, original: str, base: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_term": str(base.get("glossaryMatch") or _clean_zh_query(original)),
            "source_language": str(base.get("detectedLanguage") or "zh"),
            "canonical_term": str(base["effectiveQuery"]),
            "canonical_language": "en",
            "aliases": [original, str(base.get("glossaryMatch") or "")],
            "related_terms": list(base.get("normalizedTerms") or []),
            "historical_terms": list(base.get("historicalTerms") or []),
            "sources": ["bootstrap"],
            "confidence": 0.99,
            "user_confirmed": False,
        }

    def _mapping_result(self, original: str, mode: str, mapping: dict[str, Any], source: str) -> dict[str, Any]:
        canonical = str(mapping["canonical_term"])
        confidence_score = float(mapping.get("confidence") or 0)
        confidence = "high" if confidence_score >= 0.85 else "medium" if confidence_score >= 0.62 else "low"
        aliases = [str(item) for item in mapping.get("aliases", [])]
        matched = next((alias for alias in aliases if _compact(alias) == _compact(original)), mapping.get("source_term"))
        sources = list(mapping.get("sources") or [])
        source_label = "用户确认" if mapping.get("user_confirmed") else " / ".join(sources[:3])
        return {
            "originalQuery": original,
            "detectedLanguage": detect_query_language(original),
            "requestedMode": mode,
            "effectiveQuery": canonical,
            "normalizedTerms": list(dict.fromkeys([canonical, *mapping.get("related_terms", [])]))[:30],
            "historicalTerms": list(mapping.get("historical_terms", []))[:20],
            "translated": True,
            "glossaryMatch": matched,
            "confidence": confidence,
            "confidenceScore": round(confidence_score, 3),
            "notice": f"已将“{matched or original}”解析为英文学术术语“{canonical}”。" + (f" 依据：{source_label}。" if source_label else ""),
            "resolutionStatus": source,
            "sources": sources,
            "termMappingId": mapping.get("id"),
            "userConfirmed": bool(mapping.get("user_confirmed")),
            "aliases": aliases[:20],
        }

    @staticmethod
    def _decorate(result: dict[str, Any], mapping: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(result)
        payload.update(
            {
                "confidenceScore": 1.0 if payload.get("confidence") == "direct" else None,
                "resolutionStatus": "direct",
                "sources": [],
                "termMappingId": mapping.get("id") if mapping else None,
                "userConfirmed": bool(mapping and mapping.get("user_confirmed")),
                "aliases": list(mapping.get("aliases") or []) if mapping else [],
            }
        )
        return payload

    def _resolve_dynamic(self, original: str) -> dict[str, Any] | None:
        cleaned = _clean_zh_query(original)
        bridge = self._wikipedia_bridge(cleaned)
        if bridge is None and cleaned != original:
            bridge = self._wikipedia_bridge(original)
        if bridge is None:
            bridge = self._wikidata_direct(cleaned)
        if bridge is None:
            return None

        canonical = _academic_term(str(bridge["canonical_term"]))
        if not canonical or re.search(r"[\u3400-\u9fff]", canonical):
            return None

        aliases = list(dict.fromkeys([original, cleaned, *bridge.get("aliases", [])]))
        sources = list(dict.fromkeys(bridge.get("sources", [])))
        confidence = float(bridge.get("confidence") or 0.52)

        cso_topic, cso_related = self._validate_cso(canonical)
        if cso_topic:
            sources.append("CSO 3.5")
            confidence += 0.14

        nist_term = self._validate_nist(canonical)
        if nist_term:
            sources.append("NIST CSRC")
            confidence += 0.12

        openalex_hits, academic_ratio, openalex_terms = self._validate_openalex(canonical)
        if openalex_hits and academic_ratio >= 0.34:
            sources.append("OpenAlex")
            confidence += min(0.18, 0.10 + academic_ratio * 0.1)
        elif openalex_hits == 0:
            confidence -= 0.15

        # A cross-language Wikipedia/Wikidata bridge plus any independent academic
        # validator is enough for automatic caching. One weak source alone is not.
        confidence = max(0.0, min(confidence, 0.99))
        related = list(dict.fromkeys([canonical, *cso_related, *openalex_terms]))[:30]
        return {
            "source_term": cleaned,
            "source_language": detect_query_language(original),
            "canonical_term": canonical,
            "canonical_language": "en",
            "aliases": aliases[:40],
            "related_terms": related,
            "historical_terms": [],
            "sources": list(dict.fromkeys(sources)),
            "confidence": confidence,
            "wikidata_id": bridge.get("wikidata_id") or "",
            "nist_term": nist_term or "",
            "cso_topic": cso_topic or "",
            "openalex_hits": openalex_hits,
            "user_confirmed": False,
        }

    def _wikipedia_bridge(self, query: str) -> dict[str, Any] | None:
        response = self.session.get(
            WIKIPEDIA_API,
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 5},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
        if not isinstance(results, list):
            return None
        for rank, result in enumerate(results[:4]):
            title = str(result.get("title") or "").strip()
            if not title:
                continue
            detail = self.session.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "prop": "langlinks|pageprops",
                    "titles": title,
                    "lllang": "en",
                    "lllimit": 5,
                    "format": "json",
                },
                timeout=8,
            )
            detail.raise_for_status()
            pages = detail.json().get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {}) if isinstance(pages, dict) else {}
            langlinks = page.get("langlinks") or []
            english = next((item.get("*") for item in langlinks if item.get("lang") == "en" and item.get("*")), None)
            if not english:
                continue
            qid = str((page.get("pageprops") or {}).get("wikibase_item") or "")
            aliases: list[str] = [title]
            description = ""
            if qid:
                entity = self._wikidata_entity(qid)
                aliases.extend(entity.get("aliases", []))
                description = str(entity.get("description") or "")
                english = str(entity.get("english_label") or english)
            context_bonus = 0.08 if any(hint in description.casefold() for hint in CRYPTO_EVIDENCE) else 0.0
            return {
                "canonical_term": english,
                "aliases": aliases,
                "wikidata_id": qid,
                "sources": ["Chinese Wikipedia", "Wikidata"] if qid else ["Chinese Wikipedia"],
                "confidence": max(0.5, 0.67 - rank * 0.06 + context_bonus),
            }
        return None

    def _wikidata_direct(self, query: str) -> dict[str, Any] | None:
        response = self.session.get(
            WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "zh",
                "uselang": "en",
                "format": "json",
                "type": "item",
                "limit": 5,
            },
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("search") or []
        for rank, item in enumerate(results[:5]):
            label = str(item.get("label") or "").strip()
            if not label or re.search(r"[\u3400-\u9fff]", label):
                continue
            description = str(item.get("description") or "")
            qid = str(item.get("id") or "")
            entity = self._wikidata_entity(qid) if qid else {}
            aliases = [str((item.get("match") or {}).get("text") or query), *entity.get("aliases", [])]
            context_bonus = 0.08 if any(hint in description.casefold() for hint in CRYPTO_EVIDENCE) else 0.0
            return {
                "canonical_term": entity.get("english_label") or label,
                "aliases": aliases,
                "wikidata_id": qid,
                "sources": ["Wikidata"],
                "confidence": max(0.45, 0.60 - rank * 0.05 + context_bonus),
            }
        return None

    def _wikidata_entity(self, qid: str) -> dict[str, Any]:
        if not re.fullmatch(r"Q\d+", qid):
            return {}
        response = self.session.get(
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": qid,
                "props": "labels|aliases|descriptions",
                "languages": "zh|zh-hans|zh-cn|en",
                "format": "json",
            },
            timeout=8,
        )
        response.raise_for_status()
        entity = (response.json().get("entities") or {}).get(qid) or {}
        labels = entity.get("labels") or {}
        aliases_data = entity.get("aliases") or {}
        aliases: list[str] = []
        for lang in ("zh", "zh-hans", "zh-cn", "en"):
            aliases.extend(str(item.get("value")) for item in aliases_data.get(lang, []) if item.get("value"))
        description = ((entity.get("descriptions") or {}).get("en") or {}).get("value") or ""
        english_label = (labels.get("en") or {}).get("value") or ""
        return {"english_label": english_label, "aliases": aliases, "description": description}

    def _validate_openalex(self, term: str) -> tuple[int, float, list[str]]:
        try:
            works = self.openalex.search_works(term, limit=12, sort="relevance")
        except (requests.RequestException, ValueError):
            return 0, 0.0, []
        if not works:
            return 0, 0.0, []
        academic = 0
        topics: Counter[str] = Counter()
        for work in works:
            text = " ".join(
                str(work.get(key) or "") for key in ("title", "abstract", "primaryTopic", "venue")
            ).casefold()
            if any(hint in text for hint in CRYPTO_EVIDENCE):
                academic += 1
            topic = str(work.get("primaryTopic") or "").strip()
            if topic:
                topics[topic] += 1
        return len(works), academic / len(works), [item for item, _ in topics.most_common(5)]

    def _load_cso(self) -> None:
        with self._cso_lock:
            if self._cso_topics and time.time() - self._cso_loaded_at < 24 * 3600:
                return
            response = self.session.get(CSO_CSV_ZIP, timeout=20)
            response.raise_for_status()
            if len(response.content) > 8 * 1024 * 1024:
                raise ValueError("CSO archive unexpectedly large")
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                names = [name for name in archive.namelist() if name.endswith(".csv")]
                if len(names) != 1:
                    raise ValueError("Unexpected CSO archive")
                topics: set[str] = set()
                related: dict[str, set[str]] = defaultdict(set)
                with io.TextIOWrapper(archive.open(names[0]), encoding="utf-8") as stream:
                    for row in csv.reader(stream):
                        if len(row) < 3:
                            continue
                        left = self._cso_uri_topic(row[0])
                        right = self._cso_uri_topic(row[2])
                        if left:
                            topics.add(left)
                        if right:
                            topics.add(right)
                        if left and right and ("relatedEquivalent" in row[1] or "superTopicOf" in row[1]):
                            related[left].add(right)
                            related[right].add(left)
                self._cso_topics = topics
                self._cso_related = related
                self._cso_loaded_at = time.time()

    @staticmethod
    def _cso_uri_topic(value: str) -> str:
        if "/topics/" not in value:
            return ""
        topic = value.split("/topics/", 1)[1].rstrip(">")
        return _normalize_topic(topic)

    def _validate_cso(self, term: str) -> tuple[str | None, list[str]]:
        try:
            self._load_cso()
        except Exception:
            logger.warning("CSO terminology validation unavailable", exc_info=True)
            return None, []
        normalized = _normalize_topic(term)
        candidates = [normalized]
        if normalized.endswith("s"):
            candidates.append(normalized[:-1])
        else:
            candidates.append(normalized + "s")
        matched = next((candidate for candidate in candidates if candidate in self._cso_topics), None)
        if matched is None:
            return None, []
        related = sorted(self._cso_related.get(matched, set()))[:8]
        return matched, related

    def _validate_nist(self, term: str) -> str | None:
        candidates = [term]
        simplified = re.sub(r"\b(attacks?|schemes?|proofs?|protocols?)\b", "", term, flags=re.I).strip(" -")
        if simplified and simplified.casefold() != term.casefold():
            candidates.append(simplified)
        for candidate in candidates[:2]:
            slug = re.sub(r"[^a-z0-9]+", "_", candidate.casefold()).strip("_")
            if not slug:
                continue
            try:
                response = self.session.get(f"{NIST_GLOSSARY_BASE}/{slug}", timeout=8)
            except requests.RequestException:
                continue
            if response.status_code != 200:
                continue
            body = response.text.casefold()
            if "glossary" in body and candidate.casefold().replace("-", " ") in body.replace("-", " "):
                return candidate
        return None
