import re
from typing import Any


SEARCH_LANGUAGE_MODES = {"academic_en", "original"}


GLOSSARY: list[dict[str, Any]] = [
    {
        "canonical": "symmetric-key cryptography",
        "zh": ["对称加密", "对称密码", "对称密码学", "秘密密钥密码", "秘密密钥加密"],
        "en": ["symmetric encryption", "symmetric-key cryptography", "secret-key cryptography"],
        "related": ["symmetric encryption", "secret-key cryptography", "block ciphers", "stream ciphers"],
        "historical": ["Communication Theory of Secrecy Systems", "Feistel cipher", "Data Encryption Standard"],
    },
    {
        "canonical": "public-key cryptography",
        "zh": ["非对称加密", "非对称密码", "公钥密码", "公钥加密", "公钥密码学"],
        "en": ["asymmetric encryption", "public-key cryptography", "public key cryptography", "public-key cryptosystems"],
        "related": ["public-key cryptography", "public-key cryptosystems", "asymmetric encryption", "key exchange", "digital signatures"],
        "historical": ["New directions in cryptography", "public-key cryptosystems"],
    },
    {
        "canonical": "zero-knowledge proofs",
        "zh": ["零知识证明", "零知识", "零知识协议"],
        "en": ["zero knowledge", "zero-knowledge proofs", "zero knowledge proofs"],
        "related": ["zero-knowledge proofs", "interactive proofs", "knowledge complexity"],
        "historical": ["The knowledge complexity of interactive proof-systems"],
    },
    {
        "canonical": "secure multi-party computation",
        "zh": ["多方安全计算", "安全多方计算", "多方计算", "安全计算"],
        "en": ["secure multiparty computation", "secure multi-party computation", "mpc"],
        "related": ["secure multi-party computation", "secure multiparty computation", "MPC"],
        "historical": ["Protocols for secure computations"],
    },
    {
        "canonical": "homomorphic encryption",
        "zh": ["同态加密", "全同态加密", "部分同态加密"],
        "en": ["homomorphic encryption", "fully homomorphic encryption"],
        "related": ["homomorphic encryption", "fully homomorphic encryption", "privacy homomorphisms"],
        "historical": ["On data banks and privacy homomorphisms"],
    },
    {
        "canonical": "lattice-based cryptography",
        "zh": ["格密码", "格密码学", "基于格的密码", "格基密码"],
        "en": ["lattice cryptography", "lattice-based cryptography"],
        "related": ["lattice-based cryptography", "lattice cryptography", "learning with errors", "shortest vector problem"],
        "historical": ["Generating hard instances of lattice problems"],
    },
    {
        "canonical": "digital signatures",
        "zh": ["数字签名", "数字签名方案", "签名方案"],
        "en": ["digital signatures", "digital signature schemes"],
        "related": ["digital signatures", "signature schemes", "public-key signatures"],
        "historical": ["A method for obtaining digital signatures and public-key cryptosystems"],
    },
    {
        "canonical": "cryptographic hash functions",
        "zh": ["哈希函数", "密码哈希", "密码学哈希", "散列函数", "密码散列函数"],
        "en": ["cryptographic hash functions", "hash functions"],
        "related": ["cryptographic hash functions", "universal hashing", "collision resistance"],
        "historical": ["Universal classes of hash functions"],
    },
    {
        "canonical": "searchable encryption",
        "zh": ["可搜索加密", "可检索加密", "可搜索密码"],
        "en": ["searchable encryption", "searchable symmetric encryption"],
        "related": ["searchable encryption", "searchable symmetric encryption", "encrypted search"],
        "historical": [],
    },
    {
        "canonical": "attribute-based encryption",
        "zh": ["属性基加密", "基于属性的加密", "属性加密"],
        "en": ["attribute-based encryption", "abe"],
        "related": ["attribute-based encryption", "ciphertext-policy ABE", "key-policy ABE"],
        "historical": [],
    },
    {
        "canonical": "identity-based encryption",
        "zh": ["身份基加密", "基于身份的加密", "身份加密"],
        "en": ["identity-based encryption", "ibe"],
        "related": ["identity-based encryption", "identity-based cryptography"],
        "historical": [],
    },
    {
        "canonical": "key exchange",
        "zh": ["密钥交换", "密钥协商", "密钥交换协议"],
        "en": ["key exchange", "key agreement"],
        "related": ["key exchange", "key agreement", "Diffie-Hellman"],
        "historical": ["New directions in cryptography"],
    },
    {
        "canonical": "commitment schemes",
        "zh": ["承诺方案", "承诺协议", "密码承诺"],
        "en": ["commitment schemes", "cryptographic commitments"],
        "related": ["commitment schemes", "bit commitment", "cryptographic commitments"],
        "historical": [],
    },
    {
        "canonical": "oblivious transfer",
        "zh": ["不经意传输", "茫然传输", "OT协议"],
        "en": ["oblivious transfer", "ot"],
        "related": ["oblivious transfer", "1-out-of-2 oblivious transfer"],
        "historical": ["How to exchange secrets by oblivious transfer"],
    },
    {
        "canonical": "threshold cryptography",
        "zh": ["门限密码", "门限密码学", "阈值密码", "门限签名"],
        "en": ["threshold cryptography", "threshold signatures"],
        "related": ["threshold cryptography", "threshold signatures", "secret sharing"],
        "historical": ["How to share a secret"],
    },
    {
        "canonical": "post-quantum cryptography",
        "zh": ["后量子密码", "后量子密码学", "抗量子密码", "抗量子密码学"],
        "en": ["post-quantum cryptography", "post quantum cryptography"],
        "related": ["post-quantum cryptography", "lattice-based cryptography", "code-based cryptography", "hash-based signatures"],
        "historical": [],
    },
    {
        "canonical": "registration-based encryption",
        "zh": ["注册基加密", "注册型加密", "基于注册的加密"],
        "en": ["registration-based encryption", "rbe"],
        "related": ["registration-based encryption", "identity-based encryption"],
        "historical": [],
    },
]


FILLER_ZH = {
    "基础", "基础理论", "论文", "开山", "开山之作", "最早", "经典", "入门", "研究",
    "学习", "相关", "方向", "理论", "原理", "核心", "代表", "最基础", "是什么", "有哪些",
}


def detect_query_language(query: str) -> str:
    has_zh = bool(re.search(r"[\u3400-\u9fff]", query))
    has_latin = bool(re.search(r"[A-Za-z]", query))
    if has_zh and has_latin:
        return "mixed"
    if has_zh:
        return "zh"
    return "en"


def _compact(value: str) -> str:
    return re.sub(r"[\s\-_/·，。！？、：；（）()\[\]{}]+", "", value.casefold())


def _entry_for_english(query: str) -> dict[str, Any] | None:
    normalized = query.casefold().strip()
    for entry in GLOSSARY:
        aliases = [entry["canonical"], *entry["en"]]
        if any(alias.casefold() in normalized or normalized in alias.casefold() for alias in aliases):
            return entry
    return None


def _entry_for_chinese(query: str) -> tuple[dict[str, Any] | None, str | None, str]:
    compact = _compact(query)
    matches: list[tuple[int, dict[str, Any], str]] = []
    for entry in GLOSSARY:
        for alias in entry["zh"]:
            alias_compact = _compact(alias)
            if alias_compact and alias_compact in compact:
                matches.append((len(alias_compact), entry, alias))
    if not matches:
        return None, None, compact
    _, entry, alias = max(matches, key=lambda item: item[0])
    return entry, alias, compact.replace(_compact(alias), "", 1)


def normalize_query(query: str, mode: str = "academic_en") -> dict[str, Any]:
    original = query.strip()
    if mode not in SEARCH_LANGUAGE_MODES:
        raise ValueError("unsupported search language mode")
    language = detect_query_language(original)

    if mode == "original":
        entry = _entry_for_english(original) if language == "en" else None
        return {
            "originalQuery": original,
            "detectedLanguage": language,
            "requestedMode": mode,
            "effectiveQuery": original,
            "normalizedTerms": [original],
            "historicalTerms": list(entry.get("historical", [])) if entry else [],
            "translated": False,
            "glossaryMatch": None,
            "confidence": "direct",
            "notice": "使用原始检索词，不进行中文密码学术语转换。",
        }

    if language == "en":
        entry = _entry_for_english(original)
        return {
            "originalQuery": original,
            "detectedLanguage": language,
            "requestedMode": mode,
            "effectiveQuery": original,
            "normalizedTerms": [original, *(entry.get("related", []) if entry else [])],
            "historicalTerms": list(entry.get("historical", [])) if entry else [],
            "translated": False,
            "glossaryMatch": None,
            "confidence": "direct",
            "notice": "检测到英文关键词，直接使用原词进行学术检索。",
        }

    entry, matched_alias, residual = _entry_for_chinese(original)
    if entry is None:
        return {
            "originalQuery": original,
            "detectedLanguage": language,
            "requestedMode": mode,
            "effectiveQuery": original,
            "normalizedTerms": [original],
            "historicalTerms": [],
            "translated": False,
            "glossaryMatch": None,
            "confidence": "low",
            "notice": "暂未识别到可靠的密码学英文学术术语，已保留中文原词。可切换“中文原词”或直接输入英文关键词。",
        }

    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]*", original)
    effective = entry["canonical"]
    if ascii_terms:
        suffix = " ".join(term for term in ascii_terms if term.casefold() not in effective.casefold())
        if suffix:
            effective = f"{effective} {suffix}"

    filler_compact = {_compact(item) for item in FILLER_ZH}
    confidence = "high" if not residual or residual in filler_compact else "medium"
    return {
        "originalQuery": original,
        "detectedLanguage": language,
        "requestedMode": mode,
        "effectiveQuery": effective,
        "normalizedTerms": list(dict.fromkeys([entry["canonical"], *entry["related"]])),
        "historicalTerms": list(entry["historical"]),
        "translated": True,
        "glossaryMatch": matched_alias,
        "confidence": confidence,
        "notice": f"已将“{matched_alias}”转换为密码学常用英文学术术语“{entry['canonical']}”。",
    }
