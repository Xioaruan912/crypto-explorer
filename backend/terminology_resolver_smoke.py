#!/usr/bin/env python3
from __future__ import annotations

import tempfile

from analyzer.terminology_resolver import TerminologyResolver
from core.research_store import ResearchStore


class FakeOpenAlex:
    pass


class FakeResolver(TerminologyResolver):
    def _wikipedia_bridge(self, query: str):
        assert query == "侧信道攻击"
        return {
            "canonical_term": "Side-channel attack",
            "aliases": ["旁路攻击", "侧信道攻击"],
            "wikidata_id": "Q2267081",
            "sources": ["Chinese Wikipedia", "Wikidata"],
            "confidence": 0.70,
        }

    def _validate_cso(self, term: str):
        assert term == "side-channel attack"
        return "side channel attack", ["differential power analysis", "timing attacks"]

    def _validate_nist(self, term: str):
        return "side channel"

    def _validate_openalex(self, term: str):
        return 12, 0.9, ["Side-channel attack", "Cryptographic engineering"]


class OfflineResolver(FakeResolver):
    def _resolve_dynamic(self, original: str):
        raise AssertionError("cached terminology should resolve without external providers")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="crypto-terms-") as temp:
        store = ResearchStore(f"{temp}/research.db")
        resolver = FakeResolver(store, FakeOpenAlex())
        first = resolver.normalize("侧信道攻击", "academic_en")
        assert first["effectiveQuery"] == "side-channel attack"
        assert first["confidence"] == "high"
        assert first["termMappingId"] is not None
        assert {"Wikidata", "CSO 3.5", "NIST CSRC", "OpenAlex"}.issubset(set(first["sources"]))

        cached = OfflineResolver(store, FakeOpenAlex()).normalize("侧信道攻击", "academic_en")
        assert cached["effectiveQuery"] == "side-channel attack"
        assert cached["resolutionStatus"] == "local"

        mapping_id = int(cached["termMappingId"])
        confirmed = store.update_term_mapping(mapping_id, {"canonical_term": "side-channel attacks", "user_confirmed": True})
        assert confirmed and confirmed["user_confirmed"] is True
        assert OfflineResolver(store, FakeOpenAlex()).normalize("旁路攻击", "academic_en")["effectiveQuery"] == "side-channel attacks"
        assert OfflineResolver(store, FakeOpenAlex()).resolve_and_persist("侧信道攻击")["canonical_term"] == "side-channel attacks"

        backup = store.export_backup()
        restored = ResearchStore(f"{temp}/restored.db")
        restored.import_backup(backup)
        restored_mapping = restored.find_term_mapping("侧信道攻击")
        assert restored_mapping and restored_mapping["canonical_term"] == "side-channel attacks"
    print("TERMINOLOGY_RESOLVER_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
