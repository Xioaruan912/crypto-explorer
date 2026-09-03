import logging
from typing import Any, Dict, List, Optional

import requests


OPENALEX_BASE_URL = "https://api.openalex.org"
logger = logging.getLogger("crypto_explorer.openalex")

SOURCE_QUERY_ALIASES = {
    "crypto": "International Cryptology Conference",
    "iacr crypto": "International Cryptology Conference",
    "asiacrypt": "International Conference on the Theory and Application of Cryptology and Information Security",
    "ieee s&p": "IEEE Symposium on Security and Privacy",
    "ieee sp": "IEEE Symposium on Security and Privacy",
    "oakland": "IEEE Symposium on Security and Privacy",
    "ccs": "ACM Conference on Computer and Communications Security",
    "acm ccs": "ACM Conference on Computer and Communications Security",
    "usenix security": "USENIX Security Symposium",
}


def _work_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.rstrip("/").split("/")[-1]


def _reconstruct_abstract(inverted_index: Any) -> Optional[str]:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None

    positions: List[tuple[int, str]] = []
    for word, indexes in inverted_index.items():
        if not isinstance(word, str) or not isinstance(indexes, list):
            continue
        for index in indexes:
            if isinstance(index, int):
                positions.append((index, word))

    if not positions:
        return None

    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


class OpenAlexClient:
    """OpenAlex adapter exposing the subset used by GraphBuilder."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CryptoExplorer/1.0"})

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{OPENALEX_BASE_URL}{path}"
        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected OpenAlex response")
        return payload

    @staticmethod
    def _normalize_work(work: Dict[str, Any]) -> Dict[str, Any]:
        authors: List[Dict[str, Optional[str]]] = []
        for authorship in work.get("authorships") or []:
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(
                    {
                        "authorId": _work_id(author.get("id")),
                        "name": name,
                    }
                )

        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        best_oa_location = work.get("best_oa_location") or {}
        open_access = work.get("open_access") or {}
        primary_topic = work.get("primary_topic") or {}
        doi = work.get("doi")
        if isinstance(doi, str):
            doi = doi.removeprefix("https://doi.org/")

        referenced_works = work.get("referenced_works") or []
        paper_id = _work_id(work.get("id"))
        if not paper_id:
            raise ValueError("OpenAlex work is missing an ID")

        return {
            "paperId": paper_id,
            "title": work.get("display_name") or work.get("title") or "Unknown",
            "authors": authors,
            "year": work.get("publication_year"),
            "venue": source.get("display_name") or primary_location.get("raw_source_name"),
            "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
            "tldr": None,
            "citationCount": work.get("cited_by_count") or 0,
            "referenceCount": len(referenced_works),
            "url": primary_location.get("landing_page_url") or work.get("id"),
            "externalIds": {"DOI": doi} if doi else {},
            "openAccessPdf": {"url": best_oa_location.get("pdf_url")}
            if best_oa_location.get("pdf_url")
            else None,
            "isOpenAccess": bool(open_access.get("is_oa")),
            "publicationDate": work.get("publication_date"),
            "workType": work.get("type"),
            "primaryTopic": primary_topic.get("display_name"),
        }

    def search_works(
        self,
        query: str,
        limit: int = 25,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        sort: str = "relevance",
        open_access_only: bool = False,
    ) -> List[Dict[str, Any]]:
        requested_limit = max(1, min(limit, 100))
        params: Dict[str, Any] = {
            "search": query,
            # Keep OpenAlex relevance ranking first, then apply the requested
            # secondary sort locally. Sorting the API by citations can surface
            # very highly cited but weakly matching papers.
            "per_page": requested_limit,
        }
        filters: List[str] = []
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")
        if open_access_only:
            filters.append("open_access.is_oa:true")
        if filters:
            params["filter"] = ",".join(filters)
        logger.info(
            "work discovery query=%r limit=%s from_year=%s to_year=%s sort=%s oa=%s",
            query,
            limit,
            from_year,
            to_year,
            sort,
            open_access_only,
        )
        payload = self._request("/works", params)
        results = payload.get("results") or []
        normalized = [self._normalize_work(work) for work in results if isinstance(work, dict)]
        if sort == "citations":
            normalized.sort(key=lambda item: item.get("citationCount") or 0, reverse=True)
        elif sort == "foundational":
            normalized.sort(
                key=lambda item: (
                    item.get("year") if item.get("year") is not None else 9999,
                    -(item.get("citationCount") or 0),
                )
            )
        elif sort == "newest":
            normalized.sort(
                key=lambda item: (item.get("publicationDate") or "", item.get("citationCount") or 0),
                reverse=True,
            )
        return normalized[:requested_limit]

    def search_authors(self, query: str, limit: int = 20, sort: str = "relevance") -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"search": query, "per_page": max(1, min(limit, 50))}
        payload = self._request("/authors", params)
        items: List[Dict[str, Any]] = []
        for author in payload.get("results") or []:
            if not isinstance(author, dict):
                continue
            institutions = [
                inst.get("display_name")
                for inst in (author.get("last_known_institutions") or [])
                if isinstance(inst, dict) and inst.get("display_name")
            ]
            items.append(
                {
                    "id": _work_id(author.get("id")),
                    "name": author.get("display_name") or "Unknown author",
                    "worksCount": author.get("works_count") or 0,
                    "citedByCount": author.get("cited_by_count") or 0,
                    "institutions": institutions,
                    "orcid": author.get("orcid"),
                    "openAlexUrl": author.get("id"),
                }
            )
        if sort == "citations":
            items.sort(key=lambda item: item["citedByCount"], reverse=True)
        elif sort == "works":
            items.sort(key=lambda item: item["worksCount"], reverse=True)
        return items

    def get_author(self, author_id: str, works_limit: int = 12) -> Dict[str, Any]:
        author_id = _work_id(author_id) or author_id
        author = self._request(f"/authors/{author_id}", {})
        works_payload = self._request(
            "/works",
            {
                "filter": f"authorships.author.id:{author_id}",
                "sort": "cited_by_count:desc",
                "per_page": max(1, min(works_limit, 50)),
            },
        )
        institutions = [
            inst.get("display_name")
            for inst in (author.get("last_known_institutions") or [])
            if isinstance(inst, dict) and inst.get("display_name")
        ]
        return {
            "id": author_id,
            "name": author.get("display_name") or "Unknown author",
            "worksCount": author.get("works_count") or 0,
            "citedByCount": author.get("cited_by_count") or 0,
            "institutions": institutions,
            "orcid": author.get("orcid"),
            "openAlexUrl": author.get("id"),
            "topWorks": [
                self._normalize_work(work)
                for work in (works_payload.get("results") or [])
                if isinstance(work, dict)
            ],
        }

    def search_sources(self, query: str, limit: int = 20, sort: str = "relevance") -> List[Dict[str, Any]]:
        resolved_query = SOURCE_QUERY_ALIASES.get(query.strip().casefold(), query)
        params: Dict[str, Any] = {"search": resolved_query, "per_page": max(1, min(limit, 50))}
        payload = self._request("/sources", params)
        items = [self._normalize_source(source) for source in payload.get("results") or [] if isinstance(source, dict)]
        if sort == "citations":
            items.sort(key=lambda item: item["citedByCount"], reverse=True)
        elif sort == "works":
            items.sort(key=lambda item: item["worksCount"], reverse=True)
        return items

    @staticmethod
    def _normalize_source(source: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": _work_id(source.get("id")),
            "name": source.get("display_name") or "Unknown source",
            "type": source.get("type"),
            "worksCount": source.get("works_count") or 0,
            "citedByCount": source.get("cited_by_count") or 0,
            "issn": source.get("issn_l") or ((source.get("issn") or [None])[0]),
            "homepageUrl": source.get("homepage_url"),
            "isOpenAccess": bool(source.get("is_oa")),
            "isInDoaj": bool(source.get("is_in_doaj")),
            "hostOrganization": source.get("host_organization_name"),
            "openAlexUrl": source.get("id"),
        }

    def get_source(self, source_id: str, works_limit: int = 12) -> Dict[str, Any]:
        source_id = _work_id(source_id) or source_id
        source = self._request(f"/sources/{source_id}", {})
        works_payload = self._request(
            "/works",
            {
                "filter": f"primary_location.source.id:{source_id}",
                "sort": "cited_by_count:desc",
                "per_page": max(1, min(works_limit, 50)),
            },
        )
        result = self._normalize_source(source)
        result["topWorks"] = [
            self._normalize_work(work)
            for work in (works_payload.get("results") or [])
            if isinstance(work, dict)
        ]
        return result

    def search_paper(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        logger.info("search query=%r limit=%s", query, limit)
        payload = self._request(
            "/works",
            {
                "search": query,
                "per_page": max(1, min(limit, 25)),
            },
        )
        results = payload.get("results") or []
        return [self._normalize_work(work) for work in results if isinstance(work, dict)]

    def get_citations(self, paper_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        logger.info("citation fetch paper_id=%s limit=%s", paper_id, limit)
        payload = self._request(
            "/works",
            {
                "filter": f"cites:{paper_id}",
                "sort": "cited_by_count:desc",
                "per_page": max(1, min(limit, 100)),
            },
        )
        results = payload.get("results") or []
        return [self._normalize_work(work) for work in results if isinstance(work, dict)]

