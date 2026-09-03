#!/usr/bin/env python3
from analyzer.concept_genealogy import ConceptGenealogyEngine, _crypto_like, _draw_eligible


def work(paper_id, title, year, citations=1000, refs=None, topic="Cryptography and Data Security", abstract="cryptography security encryption protocol"):
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [],
        "year": year,
        "venue": "Test Venue",
        "abstract": abstract,
        "citationCount": citations,
        "referenceCount": len(refs or []),
        "referencedWorkIds": refs or [],
        "url": f"https://openalex.org/{paper_id}",
        "externalIds": {},
        "openAccessPdf": None,
        "primaryTopic": topic,
    }


class FakeClient:
    def __init__(self):
        self.works = {
            "W-ND": work("W-ND", "New directions in cryptography", 1976, 14000),
            "W-RSA": work("W-RSA", "A method for obtaining digital signatures and public-key cryptosystems", 1978, 13000, ["W-ND"]),
            "W-ELG": work("W-ELG", "A public key cryptosystem and a signature scheme based on discrete logarithms", 1985, 7000, ["W-ND"]),
            "W-OAEP": work("W-OAEP", "Optimal asymmetric encryption", 1995, 900, ["W-RSA", "W-ND"]),
            "W-ASYM": work("W-ASYM", "Symmetric and Asymmetric Encryption", 1979, 200, ["W-ND"]),
            "W-AE": work("W-AE", "Anamorphic Encryption: Private Communication Against a Dictator", 2022, 40, ["W-RSA"]),
            "W-AE2": work("W-AE2", "Anamorphic Encryption, Revisited", 2024, 20, ["W-AE", "W-RSA"]),
        }

    def search_works(self, query, limit=25, **kwargs):
        normalized = query.casefold()
        if normalized == "asymmetric encryption":
            return [self.works["W-OAEP"], self.works["W-ASYM"]][:limit]
        if normalized == "new directions in cryptography":
            return [self.works["W-ND"]][:limit]
        if normalized == "anamorphic encryption":
            return [self.works["W-AE"], self.works["W-AE2"]][:limit]
        return []

    def get_works_by_ids(self, work_ids, **kwargs):
        return [self.works[work_id] for work_id in work_ids if work_id in self.works]

    def get_citations(self, paper_id, limit=100):
        items = [work for work in self.works.values() if paper_id in (work.get("referencedWorkIds") or [])]
        items.sort(key=lambda item: item.get("citationCount") or 0, reverse=True)
        return items[:limit]


def main():
    assert _draw_eligible(work("W-X", "New directions in cryptography", 1976))
    assert _draw_eligible(work("W-S", "Communication Theory of Secrecy Systems", 1949))
    assert not _draw_eligible(work("W-K", "The Art of Computer Programming. Volume 2", 1970))
    assert not _crypto_like(work("W-I", "Anamorphic Signature Identification from Images", 2007, topic="Handwritten Text Recognition Techniques", abstract="image segmentation handwriting recognition"))
    engine = ConceptGenealogyEngine(FakeClient(), cache_ttl=1)
    asymmetric = engine.build("asymmetric encryption", pool_size=12)
    assert asymmetric["origin"]["paper"]["paperId"] == "W-ND"
    assert asymmetric["historicalQuery"] == "New directions in cryptography"
    assert [stage["stage"] for stage in asymmetric["learningPath"]] == ["开山论文", "早期奠基", "关键演进", "现代代表"]
    path_years = [paper["paper"]["year"] for stage in asymmetric["learningPath"] for paper in stage["papers"]]
    assert path_years == sorted(path_years), path_years
    assert path_years[0] == 1976

    anamorphic = engine.build("Anamorphic Encryption", pool_size=12)
    assert anamorphic["origin"]["paper"]["paperId"] == "W-AE"
    assert anamorphic["historicalQuery"] is None
    anamorphic_years = [paper["paper"]["year"] for stage in anamorphic["learningPath"] for paper in stage["papers"]]
    assert anamorphic_years == sorted(anamorphic_years), anamorphic_years
    print("GENEALOGY_SMOKE=PASS")


if __name__ == "__main__":
    main()
