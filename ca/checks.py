import re
from dataclasses import dataclass
from itertools import combinations

CJK = re.compile("[\u4e00-\u9fff]")
LATIN = re.compile("[A-Za-z]")
DISCOUNT = "(?:折扣|优惠|打折|折)"
REFUSAL = "(?:没有|不能|不提供)"
REFUSES_DISCOUNT = re.compile(f"{REFUSAL}.{{0,6}}{DISCOUNT}|{DISCOUNT}.{{0,6}}{REFUSAL}")
OVERLAP_LIMIT = 0.75
CHINESE_RATIO = 0.90
CAPACITY_WORDS = ("仅限", "限量", "名额", "限定")


@dataclass
class Check:
    name: str
    passed: bool
    reason: str = ""


def bigrams(text):
    return {text[i : i + 2] for i in range(len(text) - 1)}


def overlap(a, b):
    a, b = bigrams(a), bigrams(b)
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def chinese_ratio(text, allowed_names):
    for name in allowed_names:
        text = text.replace(name, "")
    cjk, latin = len(CJK.findall(text)), len(LATIN.findall(text))
    return cjk / (cjk + latin) if cjk + latin else 1.0


def flagged(name, texts, bad):
    hits = [i for i, text in enumerate(texts) if bad(text)]
    return Check(name, not hits, f"candidates {hits}" if hits else "")


def check_candidates(candidates, brand, scenario, product_ids, owned_ids, event):
    rules = brand.rules
    texts = [c["text"] for c in candidates]
    limits = rules["lengths"]
    max_length = limits["max"]
    allowed_ids = set(product_ids) | set(owned_ids)
    outside = [p["name"] for p in brand.catalog if p["id"] not in allowed_ids]
    menu = brand.menus[scenario]
    strategies = [c["strategy"] for c in candidates]
    has_capacity = bool(event and event.get("capacity"))

    def too_long(candidate):
        low, high = limits.get(candidate["length"], (0, -1))
        return not low <= len(candidate["text"]) <= min(high, max_length)

    close = [
        (i, j) for (i, a), (j, b) in combinations(enumerate(texts), 2)
        if overlap(a, b) > rules.get("overlap_limit", OVERLAP_LIMIT)
    ]
    bad_length = [i for i, c in enumerate(candidates) if too_long(c)]
    bad_menu = [i for i, s in enumerate(strategies) if s not in menu]
    repeated = [s for s in set(strategies) if strategies.count(s) > 1]

    return [
        Check("count", len(texts) == 3 and all(t.strip() for t in texts), f"got {len(texts)} texts"),
        flagged("chinese", texts, lambda t: chinese_ratio(t, rules["allowed_english"]) < rules.get("chinese_ratio", CHINESE_RATIO)),
        Check("length", not bad_length, f"candidates {bad_length}" if bad_length else ""),
        Check("overlap", not close, f"pairs {close}" if close else ""),
        Check("menu", not bad_menu, f"candidates {bad_menu}" if bad_menu else ""),
        Check("distinct_strategies", not repeated, f"repeated {repeated}" if repeated else ""),
        flagged("forbidden", texts, lambda t: any(w in t for w in rules["forbidden"])),
        flagged(
            "offer", texts,
            lambda t: any(p in t for p in rules["offer_patterns"]) and not REFUSES_DISCOUNT.search(t),
        ),
        flagged("product", texts, lambda t: any(n in t for n in outside)),
        flagged("capacity", texts, lambda t: not has_capacity and any(w in t for w in CAPACITY_WORDS)),
    ]
