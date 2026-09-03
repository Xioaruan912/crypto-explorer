#!/usr/bin/env python3
from __future__ import annotations

import tempfile

from analyzer.canonical_metadata import CanonicalMetadataResolver
from core.research_store import ResearchStore


def work(paper_id: str, title: str, author: str, year: int, venue: str) -> dict:
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [{"name": author}],
        "year": year,
        "venue": venue,
        "externalIds": {},
    }


class FakeResolver(CanonicalMetadataResolver):
    def _dblp_candidates(self, title: str, first_author: str):
        if title.startswith("A Method"):
            return [
                {"title": title + " (Reprint).", "year": 1983, "venue": "Commun. ACM", "doi": "reprint", "dblpUrl": "reprint", "source": "DBLP", "similarity": 1.0, "authorMatch": True},
                {"title": title + ".", "year": 1978, "venue": "Commun. ACM", "doi": "original", "dblpUrl": "original", "source": "DBLP", "similarity": 1.0, "authorMatch": True},
            ]
        if title.startswith("Identity-Based"):
            return [
                {"title": title + ".", "year": 1984, "venue": "CRYPTO", "doi": None, "dblpUrl": "shamir84", "source": "DBLP", "similarity": 1.0, "authorMatch": True},
            ]
        return []

    def _crossref_candidates(self, title: str, first_author: str, doi):
        if title.startswith("Self-Certified"):
            return [
                {"title": title, "year": 1991, "venue": "EUROCRYPT '91", "doi": "girault91", "source": "Crossref", "similarity": 1.0, "authorMatch": True},
            ]
        return []


class FakeOpenAlex:
    def search_works(self, title, limit=8, sort="foundational"):
        if title.startswith("Quantum cryptography"):
            return [
                work("WO", "Quantum cryptography: Public key distribution and coin tossing", "C. H. Bennett", 1984, "International Conference on Computers, Systems & Signal Processing"),
                work("WR", "Quantum cryptography: Public key distribution and coin tossing", "C. H. Bennett", 2020, "Theoretical Computer Science"),
            ]
        return []


class FallbackResolver(CanonicalMetadataResolver):
    def _dblp_candidates(self, title: str, first_author: str):
        return []

    def _crossref_candidates(self, title: str, first_author: str, doi):
        return []


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="crypto-canonical-") as temp:
        resolver = FakeResolver(ResearchStore(f"{temp}/research.db"))
        rsa = resolver.canonicalize(work("W1", "A Method for Obtaining Digital Signatures and Public-Key Cryptosystems", "Ronald L. Rivest", 1983, "Communications of the ACM"))
        shamir = resolver.canonicalize(work("W2", "Identity-Based Cryptosystems and Signature Schemes", "Adi Shamir", 2007, "Lecture Notes in Computer Science"))
        girault = resolver.canonicalize(work("W3", "Self-Certified Public Keys", "Marc Girault", 2007, "Lecture Notes in Computer Science"))
        assert (rsa["year"], rsa["sourceYear"], rsa["canonicalSource"]) == (1978, 1983, "DBLP")
        assert (shamir["year"], shamir["sourceYear"], shamir["venue"]) == (1984, 2007, "CRYPTO")
        assert (girault["year"], girault["sourceYear"], girault["venue"]) == (1991, 2007, "EUROCRYPT '91")
        fallback = FallbackResolver(ResearchStore(f"{temp}/fallback.db"), FakeOpenAlex())
        quantum = fallback.canonicalize(work("W4", "Quantum cryptography: Public key distribution and coin tossing", "C. H. Bennett", 2020, "Theoretical Computer Science"))
        assert (quantum["year"], quantum["sourceYear"], quantum["canonicalSource"]) == (1984, 2020, "OpenAlex duplicate resolution")
        assert quantum["isReprintLike"] is True
    print("CANONICAL_METADATA_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
