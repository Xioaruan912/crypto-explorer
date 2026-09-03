from analyzer.query_normalizer import normalize_query


def main() -> None:
    symmetric = normalize_query("对称加密", "academic_en")
    assert symmetric["effectiveQuery"] == "symmetric-key cryptography"
    assert symmetric["detectedLanguage"] == "zh"
    assert symmetric["translated"] is True
    assert "Communication Theory of Secrecy Systems" in symmetric["historicalTerms"]

    asymmetric = normalize_query("非对称加密", "academic_en")
    assert asymmetric["effectiveQuery"] == "public-key cryptography"
    assert "New directions in cryptography" in asymmetric["historicalTerms"]

    mixed = normalize_query("对称加密 AES", "academic_en")
    assert mixed["effectiveQuery"] == "symmetric-key cryptography AES"
    assert mixed["detectedLanguage"] == "mixed"

    original = normalize_query("对称加密", "original")
    assert original["effectiveQuery"] == "对称加密"
    assert original["translated"] is False

    english = normalize_query("Anamorphic Encryption", "academic_en")
    assert english["effectiveQuery"] == "Anamorphic Encryption"
    assert english["detectedLanguage"] == "en"

    unknown = normalize_query("隐身变形密码", "academic_en")
    assert unknown["effectiveQuery"] == "隐身变形密码"
    assert unknown["confidence"] == "low"

    print("QUERY_NORMALIZER_SMOKE=PASS")


if __name__ == "__main__":
    main()
