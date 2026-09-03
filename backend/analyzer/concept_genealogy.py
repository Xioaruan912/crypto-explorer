import math
import logging
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from analyzer.canonical_metadata import CanonicalMetadataResolver
from fetchers.openalex import OpenAlexClient


logger = logging.getLogger("crypto_explorer.concept_genealogy")


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

    def __init__(
        self,
        client: OpenAlexClient,
        cache_ttl: int = 900,
        canonical_resolver: CanonicalMetadataResolver | None = None,
    ) -> None:
        self.client = client
        self.canonical_resolver = canonical_resolver
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
            coverage = len(candidate.anchors) / max(1, len(anchor_ids))
            if candidate.distance == 2 and not _title_crypto_like(work) and coverage < 0.4:
                continue
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
        if origin and self.canonical_resolver is not None:
            origin["paper"] = self.canonical_resolver.canonicalize(origin["paper"])
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

        evolution = self._build_forward_evolution(
            query,
            origin,
            anchors,
            from_year=from_year,
            to_year=to_year,
        )
        learning_path = evolution["learningPath"]
        forward_papers = [paper for stage in learning_path[1:] for paper in stage["papers"]]
        classics = forward_papers[:3]
        current = evolution["current"] or [self._current_payload(work) for work in anchors[:3]]

        result = {
            "query": query,
            "historicalQuery": historical_query,
            "anchors": current,
            "origin": origin,
            "background": prerequisites,
            "prerequisites": prerequisites,
            "classics": classics,
            "learningPath": learning_path,
            "branches": evolution["branches"],
            "pool": pool,
            "poolCount": len(pool),
        }
        with self._cache_lock:
            if len(self._cache) >= 48:
                oldest = min(self._cache, key=lambda cache_key: self._cache[cache_key][0])
                self._cache.pop(oldest, None)
            self._cache[key] = (time.time(), result)
        return result

    def _build_forward_evolution(
        self,
        query: str,
        origin: dict[str, Any] | None,
        anchors: list[dict[str, Any]],
        from_year: int | None,
        to_year: int | None,
    ) -> dict[str, Any]:
        """After finding the origin, switch direction and follow cited-by edges forward.

        Genealogy answers "where did this concept come from?". This method answers
        the separate learning question "what happened after the origin?" and keeps
        the default reading path chronological by construction.
        """
        empty_path = [
            {"stage": "开山论文", "papers": [origin] if origin else []},
            {"stage": "早期奠基", "papers": []},
            {"stage": "关键演进", "papers": []},
            {"stage": "现代代表", "papers": []},
        ]
        if not origin:
            return {"learningPath": empty_path, "branches": [], "current": []}

        origin_work = origin["paper"]
        origin_id = str(origin_work.get("paperId") or "")
        origin_year = int(origin_work.get("year") or 0)
        if not origin_id or not origin_year:
            return {"learningPath": empty_path, "branches": [], "current": []}

        candidate_meta: dict[str, dict[str, Any]] = {}

        def add_work(work: dict[str, Any], distance: int) -> None:
            work_id = str(work.get("paperId") or "")
            year = work.get("year")
            if not work_id or work_id == origin_id or not year:
                return
            if year < origin_year:
                return
            if from_year is not None and year < from_year:
                return
            if to_year is not None and year > to_year:
                return
            if not _crypto_like(work):
                return
            existing = candidate_meta.get(work_id)
            if existing is None or distance < existing["distance"]:
                candidate_meta[work_id] = {"work": work, "distance": distance}

        get_citations = getattr(self.client, "get_citations", None)
        direct: list[dict[str, Any]] = []
        if callable(get_citations):
            try:
                direct = list(get_citations(origin_id, limit=100))
            except Exception:
                direct = []
        if not direct:
            direct = [work for work in anchors if (work.get("year") or 0) >= origin_year]
        for work in direct:
            add_work(work, 1)

        # Follow a bounded second hop from high-impact/relevant direct descendants.
        if callable(get_citations):
            expansion_parents = sorted(
                [item["work"] for item in candidate_meta.values() if item["distance"] == 1],
                key=lambda work: (
                    _query_overlap(query, work) * 0.45
                    + _citation_score(int(work.get("citationCount") or 0)) * 0.35
                    + (0.20 if _title_crypto_like(work) else 0),
                ),
                reverse=True,
            )[:3]
            for parent in expansion_parents:
                try:
                    descendants = get_citations(str(parent["paperId"]), limit=40)
                except Exception:
                    logger.warning("forward genealogy expansion failed paper_id=%s", parent.get("paperId"), exc_info=True)
                    continue
                for work in descendants:
                    add_work(work, 2)

        # Ensure current semantic anchors are represented even when they do not
        # directly cite the origin in OpenAlex's current top result window.
        for work in anchors:
            add_work(work, 2)

        if not candidate_meta:
            return {"learningPath": empty_path, "branches": [], "current": []}

        downstream: Counter[str] = Counter()
        candidate_ids = set(candidate_meta)
        for item in candidate_meta.values():
            for ref_id in item["work"].get("referencedWorkIds") or []:
                if ref_id in candidate_ids:
                    downstream[ref_id] += 1

        scored: list[dict[str, Any]] = []
        for work_id, item in candidate_meta.items():
            work = item["work"]
            distance = int(item["distance"])
            bridge_score = min(1.0, downstream[work_id] / 6)
            relevance = max(_query_overlap(query, work), _query_overlap(str(origin_work.get("title") or ""), work) * 0.6)
            influence = _citation_score(int(work.get("citationCount") or 0))
            distance_score = 1.0 if distance == 1 else 0.72
            score = (
                relevance * 0.30
                + influence * 0.24
                + bridge_score * 0.22
                + distance_score * 0.12
                + (0.08 if _title_crypto_like(work) else 0.0)
                + 0.04
            )
            scored.append(
                {
                    "work": work,
                    "distance": distance,
                    "bridge": int(downstream[work_id]),
                    "score": score,
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)

        # Canonicalize only the strongest milestone candidates. This fixes reprint
        # years before stage assignment without multiplying external metadata calls.
        shortlist: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for item in scored:
            title_key = " ".join(str(item["work"].get("title") or "").casefold().split())
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            work = item["work"]
            if self.canonical_resolver is not None and len(shortlist) < 12:
                try:
                    work = self.canonical_resolver.canonicalize(work)
                except Exception:
                    logger.warning("canonical metadata fallback title=%r", work.get("title"), exc_info=True)
            if work.get("isReprintLike"):
                logger.info(
                    "excluding unresolved reprint-like milestone title=%r source_year=%s candidate_year=%s",
                    work.get("title"),
                    work.get("sourceYear"),
                    work.get("year"),
                )
                continue
            canonical_year = int(work.get("year") or 0)
            if canonical_year < origin_year:
                continue
            if from_year is not None and canonical_year < from_year:
                continue
            if to_year is not None and canonical_year > to_year:
                continue
            shortlist.append({**item, "work": work})
            if len(shortlist) >= 20:
                break

        current_year = datetime.now(timezone.utc).year
        early_end = min(current_year, origin_year + 12)
        modern_start = max(origin_year + 1, current_year - 8)
        selected_ids: set[str] = set()

        def choose(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
            ranked = sorted(items, key=lambda item: item["score"], reverse=True)[:limit]
            ranked.sort(key=lambda item: (item["work"].get("year") or 9999, -int(item["work"].get("citationCount") or 0)))
            result: list[dict[str, Any]] = []
            for item in ranked:
                work_id = str(item["work"]["paperId"])
                if work_id in selected_ids:
                    continue
                selected_ids.add(work_id)
                result.append(item)
            return result

        early = choose(
            [item for item in shortlist if origin_year < int(item["work"].get("year") or 0) <= early_end],
            3,
        )
        key = choose(
            [item for item in shortlist if int(item["work"].get("year") or 0) > early_end and int(item["work"].get("year") or 0) < modern_start],
            4,
        )
        modern = choose(
            [item for item in shortlist if int(item["work"].get("year") or 0) >= modern_start],
            3,
        )

        # For short-lived/new concepts some time bands are naturally empty. Fill
        # the middle stage with the strongest remaining chronological milestones.
        if not key:
            leftovers = [
                item for item in shortlist
                if str(item["work"]["paperId"]) not in selected_ids
                and int(item["work"].get("year") or 0) > origin_year
            ]
            key = choose(leftovers, 3)

        if not modern:
            previous_years = [
                int(item["work"].get("year") or 0)
                for item in [*early, *key]
                if item["work"].get("year")
            ]
            after_year = max(previous_years, default=origin_year)
            latest_pool = [
                item for item in shortlist
                if str(item["work"]["paperId"]) not in selected_ids
                and int(item["work"].get("year") or 0) > after_year
            ]
            latest_pool.sort(
                key=lambda item: (int(item["work"].get("year") or 0), float(item.get("score") or 0)),
                reverse=True,
            )
            modern = choose(latest_pool[:10], 3)

        def payloads(items: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
            return [self._forward_payload(query, item, origin_year, stage) for item in items]

        origin_stage = [{**origin, "reason": origin.get("reason") or "这是当前主题证据最强的概念开山论文。"}]
        learning_path = [
            {"stage": "开山论文", "papers": origin_stage},
            {"stage": "早期奠基", "papers": payloads(early, "早期奠基")},
            {"stage": "关键演进", "papers": payloads(key, "关键演进")},
            {"stage": "现代代表", "papers": payloads(modern, "现代代表")},
        ]

        # Defensive monotonicity check. Canonical metadata can move a reprint back
        # decades, so enforce chronological order after canonicalization.
        last_year = origin_year
        for stage in learning_path[1:]:
            stage["papers"] = [paper for paper in stage["papers"] if int(paper["paper"].get("year") or 0) >= last_year]
            stage["papers"].sort(key=lambda paper: int(paper["paper"].get("year") or 9999))
            if stage["papers"]:
                last_year = int(stage["papers"][-1]["paper"].get("year") or last_year)

        used_ids = {
            str(paper["paper"]["paperId"])
            for stage in learning_path
            for paper in stage["papers"]
        }
        branch_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in shortlist:
            work = item["work"]
            if str(work["paperId"]) in used_ids:
                continue
            topic = str(work.get("primaryTopic") or "").strip()
            if not topic:
                continue
            branch_groups[topic].append(item)
        branches: list[dict[str, Any]] = []
        for topic, items in sorted(
            branch_groups.items(),
            key=lambda pair: max(item["score"] for item in pair[1]),
            reverse=True,
        )[:4]:
            branches.append(
                {
                    "name": topic,
                    "papers": payloads(sorted(items, key=lambda item: item["score"], reverse=True)[:2], "重要分支"),
                }
            )

        current = learning_path[-1]["papers"]
        if not current:
            latest = sorted(shortlist, key=lambda item: int(item["work"].get("year") or 0), reverse=True)[:3]
            current = payloads(latest, "现代代表")
        return {"learningPath": learning_path, "branches": branches, "current": current}

    @staticmethod
    def _forward_payload(query: str, item: dict[str, Any], origin_year: int, stage: str) -> dict[str, Any]:
        work = item["work"]
        year = int(work.get("year") or origin_year)
        bridge = int(item.get("bridge") or 0)
        distance = int(item.get("distance") or 1)
        reason = f"开山论文之后 {max(0, year - origin_year)} 年出现，属于“{stage}”阶段。"
        if distance == 1:
            reason += " 它直接引用或承接了开山论文。"
        else:
            reason += f" 它位于开山论文向后的 {distance} 层引用演化中。"
        if bridge:
            reason += f" 在当前候选子图中还有 {bridge} 篇后续工作继续沿用它。"
        return {
            "paper": _public_work(work),
            "distance": distance,
            "anchorCoverage": bridge,
            "reason": reason,
            "drawEligible": _draw_eligible(work),
            "milestoneScore": round(float(item.get("score") or 0), 4),
        }

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
