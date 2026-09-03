import math
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from fetchers.openalex import OpenAlexClient


STOPWORDS = {
    "a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "with",
    "scheme", "schemes", "method", "methods", "system", "systems", "using",
}

CRYPTO_HINTS = {
    "crypt", "cipher", "encryption", "signature", "security", "privacy", "secret",
    "zero knowledge", "multiparty", "multi-party", "oblivious", "commitment", "hash",
    "key exchange", "authentication", "pseudorandom", "lattice", "isogen", "protocol",
}

STRONG_CRYPTO_CONTEXT = {
    "cryptograph", "data security", "computer security", "public key", "public-key",
    "secret key", "zero knowledge", "zero-knowledge", "secure computation",
    "oblivious transfer", "digital signature",
}

TITLE_CRYPTO_HINTS = {
    "crypt", "cipher", "encrypt", "signature", "security", "privacy", "secret",
    "zero-knowledge", "zero knowledge", "oblivious", "commitment", "hash", "key",
    "authentication", "pseudorandom", "protocol", "rsa", "diffie", "hellman",
}

DRAW_TITLE_HINTS = TITLE_CRYPTO_HINTS | {
    "secrecy", "secure computation", "mental game", "proof system", "knowledge complexity",
    "lattice", "one-way", "trapdoor", "random oracle", "factorization", "discrete logarithm",
    "learning with errors", "learning with error", "secret sharing",
}

HISTORICAL_ORIGIN_RULES: list[tuple[set[str], str]] = [
    ({"symmetric", "encryption"}, "Communication Theory of Secrecy Systems"),
    ({"asymmetric", "encryption"}, "New directions in cryptography"),
    ({"public", "key"}, "New directions in cryptography"),
    ({"zero", "knowledge"}, "The knowledge complexity of interactive proof-systems"),
    ({"multiparty", "computation"}, "Protocols for secure computations"),
    ({"mpc"}, "Protocols for secure computations"),
    ({"lattice", "cryptography"}, "Generating hard instances of lattice problems"),
    ({"lattice"}, "Generating hard instances of lattice problems"),
    ({"hash"}, "Universal classes of hash functions"),
    ({"homomorphic", "encryption"}, "On data banks and privacy homomorphisms"),
    ({"oblivious", "transfer"}, "How to exchange secrets by oblivious transfer"),
]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1 and token not in STOPWORDS
    }


def _query_overlap(query: str, work: dict[str, Any]) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    haystack = " ".join(
        str(work.get(key) or "")
        for key in ("title", "primaryTopic", "abstract", "venue")
    )
    work_tokens = _tokens(haystack)
    return len(query_tokens & work_tokens) / len(query_tokens)


def _crypto_like(work: dict[str, Any]) -> bool:
    topic = str(work.get("primaryTopic") or "").casefold()
    context = " ".join(str(work.get(key) or "") for key in ("abstract", "venue", "primaryTopic")).casefold()
    title = str(work.get("title") or "").casefold()
    if any(hint in context for hint in STRONG_CRYPTO_CONTEXT):
        return True
    if topic:
        return any(hint in topic for hint in ("crypt", "security", "encryption", "privacy", "cipher"))
    return any(hint in title for hint in CRYPTO_HINTS)


def _title_crypto_like(work: dict[str, Any]) -> bool:
    text = str(work.get("title") or "").casefold()
    return any(hint in text for hint in TITLE_CRYPTO_HINTS)


def _draw_eligible(work: dict[str, Any]) -> bool:
    title = str(work.get("title") or "").casefold()
    return _crypto_like(work) and any(hint in title for hint in DRAW_TITLE_HINTS)


def _exact_title_concept(query: str, work: dict[str, Any]) -> bool:
    query_tokens = _tokens(query)
    title_tokens = _tokens(str(work.get("title") or ""))
    return bool(query_tokens) and query_tokens.issubset(title_tokens)


def _historical_origin_query(query: str) -> str | None:
    query_tokens = _tokens(query)
    for trigger, historical_query in HISTORICAL_ORIGIN_RULES:
        if trigger.issubset(query_tokens):
            return historical_query
    return None


def _public_work(work: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in work.items() if key != "referencedWorkIds"}


def _citation_score(count: int) -> float:
    return min(1.0, math.log1p(max(0, count)) / math.log1p(5000))


def _age_score(year: int | None, anchor_year: int) -> float:
    if not year:
        return 0.0
    delta = max(0, anchor_year - year)
    # Prefer meaningful predecessors without making "oldest wins" the dominant rule.
    if delta <= 5:
        return 0.2
    if delta <= 20:
        return 0.55
    if delta <= 50:
        return 0.9
    if delta <= 90:
        return 0.75
    return 0.45


@dataclass
class Candidate:
    work: dict[str, Any]
    distance: int
    anchors: set[str]
    search_rank: int | None = None


class ConceptGenealogyEngine:
    """Discover conceptual ancestors instead of relying on literal keyword matches."""

    def __init__(self, client: OpenAlexClient, cache_ttl: int = 900) -> None:
        self.client = client
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()

    def build(
        self,
        query: str,
        from_year: int | None = None,
        to_year: int | None = None,
        pool_size: int = 28,
    ) -> dict[str, Any]:
        key = (" ".join(query.casefold().split()), from_year, to_year, pool_size)
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and time.time() - cached[0] <= self.cache_ttl:
                return cached[1]

        search_results = self.client.search_works(query, limit=30, sort="relevance")
        anchors = [work for work in search_results[:6] if _crypto_like(work)][:5]
        if not anchors:
            anchors = search_results[:4]
        if not anchors:
            raise ValueError(f"No papers found for query: {query}")

        anchor_ids = {str(work["paperId"]) for work in anchors}
        anchor_year = max((work.get("year") or 0 for work in anchors), default=2026) or 2026
        historical_query = _historical_origin_query(query)
        historical_origin_work: dict[str, Any] | None = None
        if historical_query:
            historical_results = self.client.search_works(historical_query, limit=4, sort="relevance")
            historical_matches = [
                work for work in historical_results
                if work.get("year")
                and (from_year is None or work["year"] >= from_year)
                and (to_year is None or work["year"] <= to_year)
                and _query_overlap(historical_query, work) >= 0.6
            ]
            if historical_matches:
                historical_origin_work = min(
                    historical_matches,
                    key=lambda work: (work.get("year") or 9999, -int(work.get("citationCount") or 0)),
                )
        candidates: dict[str, Candidate] = {}

        # Search relevance is one signal, not the definition of "foundation".
        for rank, work in enumerate(search_results, start=1):
            work_id = str(work["paperId"])
            if work_id in anchor_ids:
                continue
            candidates[work_id] = Candidate(work=work, distance=0, anchors=set(), search_rank=rank)

        direct_reach: dict[str, set[str]] = defaultdict(set)
        for anchor in anchors:
            anchor_id = str(anchor["paperId"])
            for ref_id in anchor.get("referencedWorkIds") or []:
                if ref_id not in anchor_ids:
                    direct_reach[ref_id].add(anchor_id)

        # Bound external work while retaining references shared by multiple anchors first.
        direct_ids = sorted(
            direct_reach,
            key=lambda work_id: (-len(direct_reach[work_id]), work_id),
        )[:160]
        first_hop = self.client.get_works_by_ids(direct_ids)
        first_hop_ids = {str(work["paperId"]) for work in first_hop}
        for work in first_hop:
            work_id = str(work["paperId"])
            existing = candidates.get(work_id)
            rank = existing.search_rank if existing else None
            candidates[work_id] = Candidate(
                work=work,
                distance=1,
                anchors=set(direct_reach.get(work_id, set())),
                search_rank=rank,
            )

        # Expand a carefully bounded second hop from the strongest direct ancestors.
        first_hop_ranked = sorted(
            first_hop,
            key=lambda work: (
                len(direct_reach.get(str(work["paperId"]), set())),
                _citation_score(int(work.get("citationCount") or 0)),
                1 if _crypto_like(work) else 0,
            ),
            reverse=True,
        )[:18]
        second_counts: Counter[str] = Counter()
        second_reach: dict[str, set[str]] = defaultdict(set)
        for parent in first_hop_ranked:
            parent_id = str(parent["paperId"])
            parent_anchors = direct_reach.get(parent_id, set())
            for ref_id in parent.get("referencedWorkIds") or []:
                if ref_id in anchor_ids or ref_id in first_hop_ids:
                    continue
                second_counts[ref_id] += 1
                second_reach[ref_id].update(parent_anchors)

        second_ids = [work_id for work_id, _ in second_counts.most_common(300)]
        for work in self.client.get_works_by_ids(second_ids):
            work_id = str(work["paperId"])
            existing = candidates.get(work_id)
            rank = existing.search_rank if existing else None
            candidates[work_id] = Candidate(
                work=work,
                distance=2,
                anchors=set(second_reach.get(work_id, set())),
                search_rank=rank,
            )

        scored: list[tuple[float, Candidate]] = []
        for candidate in candidates.values():
            work = candidate.work
            year = work.get("year")
            if from_year is not None and (year is None or year < from_year):
                continue
            if to_year is not None and (year is None or year > to_year):
                continue
            if year and year > anchor_year:
                continue
            crypto = _crypto_like(work)
            overlap = _query_overlap(query, work)
            # Keyword-only noise is common for terms such as "anamorphic signature".
            if not crypto and candidate.distance == 0:
                continue
            if candidate.distance == 2 and not _title_crypto_like(work) and coverage < 0.4:
                continue
            coverage = len(candidate.anchors) / max(1, len(anchor_ids))
            rank_score = 0.0 if candidate.search_rank is None else max(0.0, 1 - (candidate.search_rank - 1) / 30)
            distance_score = {0: 0.2, 1: 1.0, 2: 0.72}.get(candidate.distance, 0.0)
            score = (
                coverage * 0.34
                + distance_score * 0.19
                + _citation_score(int(work.get("citationCount") or 0)) * 0.15
                + _age_score(year, anchor_year) * 0.13
                + max(overlap, rank_score * 0.7) * 0.13
                + (0.06 if crypto else 0.0)
            )
            scored.append((score, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        pool: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for _, candidate in scored:
            normalized_title = " ".join(str(candidate.work.get("title") or "").casefold().split())
            if not normalized_title or normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            pool.append(self._paper_payload(query, candidate, len(anchor_ids)))
            if len(pool) >= pool_size:
                break

        origin = self._choose_origin(query, search_results, scored, anchor_year, len(anchor_ids))
        if historical_origin_work is not None:
            origin = self._paper_payload(
                query,
                Candidate(historical_origin_work, 0, set(), None),
                len(anchor_ids),
                origin=True,
            )
            origin["reason"] = (
                f"系统将现代关键词映射到历史术语“{historical_query}”，"
                "再结合引用谱系确认这篇论文是更合适的概念源头。"
            )
        origin_id = origin["paper"]["paperId"] if origin else None
        origin_year = origin["paper"].get("year") if origin else None
        ancestors = [
            item for item in pool
            if item["paper"]["paperId"] != origin_id and item["distance"] > 0
        ]
        older_ancestors = sorted(
            [item for item in ancestors if origin_year is None or (item["paper"].get("year") or 9999) <= origin_year],
            key=lambda item: (item["paper"].get("year") or 9999, -(item["paper"].get("citationCount") or 0)),
        )
        prerequisites = older_ancestors[:2]
        if len(prerequisites) < 2:
            prerequisites.extend(item for item in ancestors if item not in prerequisites)
            prerequisites = prerequisites[:2]
        remaining = [item for item in ancestors if item not in prerequisites]
        classics = sorted(
            remaining,
            key=lambda item: (item["paper"].get("year") or 0, item["paper"].get("citationCount") or 0),
            reverse=True,
        )[:2]
        current = [self._current_payload(work) for work in anchors[:3]]

        result = {
            "query": query,
            "historicalQuery": historical_query,
            "anchors": current,
            "origin": origin,
            "prerequisites": prerequisites,
            "classics": classics,
            "learningPath": [
                {"stage": "前置基础", "papers": prerequisites[:2]},
                {"stage": "关键经典", "papers": classics[:2]},
                {"stage": "概念开山", "papers": [origin] if origin else []},
                {"stage": "当前代表", "papers": current[:2]},
            ],
            "pool": pool,
            "poolCount": len(pool),
        }
        with self._cache_lock:
            if len(self._cache) >= 48:
                oldest = min(self._cache, key=lambda cache_key: self._cache[cache_key][0])
                self._cache.pop(oldest, None)
            self._cache[key] = (time.time(), result)
        return result

    def _choose_origin(
        self,
        query: str,
        search_results: list[dict[str, Any]],
        scored: list[tuple[float, Candidate]],
        anchor_year: int,
        anchor_count: int,
    ) -> dict[str, Any] | None:
        exact_search = [
            (rank, work)
            for rank, work in enumerate(search_results[:2], start=1)
            if _title_crypto_like(work) and _exact_title_concept(query, work) and work.get("year")
        ]
        strong_search = [
            (rank, work)
            for rank, work in enumerate(search_results[:12], start=1)
            if _title_crypto_like(work) and _query_overlap(query, work) >= 0.72 and work.get("year")
        ]
        source = exact_search or strong_search
        literal_origin = min(source, key=lambda item: (item[1]["year"], item[0]))[1] if source else None

        ancestor_options = [
            (score, candidate)
            for score, candidate in scored
            if candidate.distance > 0
            and candidate.work.get("year")
            and _title_crypto_like(candidate.work)
            and len(candidate.anchors) / max(1, anchor_count) >= 0.2
        ]
        ancestor_origin = None
        if ancestor_options:
            ancestor_origin = max(
                ancestor_options,
                key=lambda item: (
                    item[0] + _age_score(item[1].work.get("year"), anchor_year) * 0.12,
                    -(item[1].work.get("year") or 9999),
                ),
            )[1]

        chosen: Candidate | None = None
        if literal_origin is not None:
            chosen = Candidate(literal_origin, 0, set(), next((i for i, w in enumerate(search_results, 1) if w["paperId"] == literal_origin["paperId"]), None))
            literal_year = literal_origin.get("year") or 9999
            # A later umbrella term may have an immediately preceding conceptual paper whose
            # title uses different language. Only allow a close historical correction; this
            # prevents a new notion such as "Anamorphic Encryption" from collapsing back to RSA.
            if anchor_year - literal_year >= 15:
                close_ancestors = [
                    (score, candidate)
                    for score, candidate in ancestor_options
                    if candidate.work.get("year")
                    and candidate.work["year"] < literal_year
                    and literal_year - candidate.work["year"] <= 12
                ]
                if close_ancestors:
                    high_impact = [
                        item for item in close_ancestors
                        if int(item[1].work.get("citationCount") or 0) >= 1000
                    ]
                    if high_impact:
                        chosen = min(
                            high_impact,
                            key=lambda item: (
                                item[1].work.get("year") or 9999,
                                -int(item[1].work.get("citationCount") or 0),
                            ),
                        )[1]
                    else:
                        chosen = max(
                            close_ancestors,
                            key=lambda item: (
                                _citation_score(int(item[1].work.get("citationCount") or 0)) * 0.45
                                + (len(item[1].anchors) / max(1, anchor_count)) * 0.25
                                + _age_score(item[1].work.get("year"), anchor_year) * 0.15
                                + item[0] * 0.15
                            ),
                        )[1]
        elif ancestor_origin is not None:
            chosen = ancestor_origin
        return self._paper_payload(query, chosen, anchor_count, origin=True) if chosen else None

    @staticmethod
    def _paper_payload(query: str, candidate: Candidate, anchor_count: int, origin: bool = False) -> dict[str, Any]:
        coverage_count = len(candidate.anchors)
        if origin:
            reason = "这是当前主题最早且证据较强的概念源头候选。"
            if candidate.distance:
                reason += f" 它位于现代代表论文的 {candidate.distance} 层引用祖先中。"
        elif candidate.distance == 1:
            reason = f"被 {max(1, coverage_count)} 篇当前代表论文直接引用，是理解该方向的重要前置工作。"
        elif candidate.distance == 2:
            reason = f"位于两层引用祖先中，并可从 {max(1, coverage_count)} 个当前研究分支回溯到。"
        else:
            reason = f"与“{query}”高度相关且较早出现，可作为概念形成阶段的补充阅读。"
        return {
            "paper": _public_work(candidate.work),
            "distance": candidate.distance,
            "anchorCoverage": coverage_count,
            "reason": reason,
            "drawEligible": _draw_eligible(candidate.work),
        }

    @staticmethod
    def _current_payload(work: dict[str, Any]) -> dict[str, Any]:
        return {
            "paper": _public_work(work),
            "distance": 0,
            "anchorCoverage": 0,
            "reason": "当前关键词下高度相关的代表论文，用作概念谱系的现代锚点。",
            "drawEligible": _draw_eligible(work),
        }
