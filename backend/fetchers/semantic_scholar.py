import requests
import time
import logging
from typing import List, Dict, Any, Optional

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = "paperId,title,authors,year,venue,abstract,tldr,citationCount,referenceCount,url,externalIds,openAccessPdf"
CITATION_FIELDS = "paperId,title,authors,year,venue,abstract,citationCount,referenceCount,url,externalIds,openAccessPdf"
logger = logging.getLogger("crypto_explorer.semantic_scholar")

def _request_with_retry(url: str, params: dict, headers: dict, retries: int = 3, backoff: int = 2) -> requests.Response:
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=12)
            if response.status_code == 429:
                if "x-api-key" not in headers:
                    logger.warning("rate limited anonymous request; returning immediately")
                    return response
                logger.warning("rate limited attempt=%s retry_in_seconds=%s", attempt + 1, backoff * (attempt + 1))
                time.sleep(backoff * (attempt + 1))
                continue
            return response
        except requests.exceptions.RequestException as e:
            logger.warning("network error attempt=%s error=%s", attempt + 1, e)
            time.sleep(backoff * (attempt + 1))
    
    return requests.get(url, params=params, headers=headers, timeout=15)

class SemanticScholarClient:
    def __init__(self, api_key: Optional[str] = None):
        self.headers = {"User-Agent": "CryptoExplorer/1.0"}
        if api_key:
            self.headers["x-api-key"] = api_key

    def search_paper(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for a paper by title/keyword."""
        url = f"{S2_BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": DEFAULT_FIELDS
        }
        response = _request_with_retry(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific paper."""
        url = f"{S2_BASE_URL}/paper/{paper_id}"
        params = {"fields": DEFAULT_FIELDS}
        response = _request_with_retry(url, params=params, headers=self.headers)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_citations(self, paper_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get papers that cite the given paper_id."""
        url = f"{S2_BASE_URL}/paper/{paper_id}/citations"
        
        # We need the citing paper details.
        citing_fields = ",".join([f"citingPaper.{f}" for f in CITATION_FIELDS.split(",")])
        params = {
            "fields": f"contexts,intents,{citing_fields}",
            "limit": limit
        }
        response = _request_with_retry(url, params=params, headers=self.headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        
        # Flatten the structure to return just the paper dicts
        data = response.json().get("data", [])
        results = []
        for item in data:
            if "citingPaper" in item and item["citingPaper"].get("paperId"):
                # Also include citation context if useful for heuristic engine
                paper = item["citingPaper"]
                paper["_citation_contexts"] = item.get("contexts", [])
                results.append(paper)
        return results

    def get_references(self, paper_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get papers that the given paper_id cites."""
        url = f"{S2_BASE_URL}/paper/{paper_id}/references"
        
        cited_fields = ",".join([f"citedPaper.{f}" for f in CITATION_FIELDS.split(",")])
        params = {
            "fields": f"contexts,intents,{cited_fields}",
            "limit": limit
        }
        response = _request_with_retry(url, params=params, headers=self.headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        
        data = response.json().get("data", [])
        results = []
        for item in data:
            if "citedPaper" in item and item["citedPaper"].get("paperId"):
                results.append(item["citedPaper"])
        return results
