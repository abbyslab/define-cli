"""
Manual live tests — all supported languages.
Run: python3 tests/test_live.py
Network required.
"""

from __future__ import annotations
from define_cli import wiktionary, reverso

SEP = "─" * 60

TEST_WORDS = {
    "fr": "bonjour",
    "nl": "ingewikkeld",
    "de": "Haus",
    "es": "casa",
    "it": "ciao",
    "pt": "obrigado",
    "ru": "привет",
    "pl": "dom",
    "uk": "привіт",
    "sv": "hus",
    "da": "hus",
    "cs": "dům",
    "sk": "dom",
    "ro": "casă",
    "hu": "ház",
    "el": "γεια",
    "tr": "ev",
    "ar": "مرحبا",
    "he": "שלום",
    "fa": "خانه",
    "hi": "नमस्ते",
    "zh": "你好",
    "ja": "猫",
    "ko": "안녕",
    "th": "บ้าน",
    "vi": "xin chào",
    "ca": "casa",
}

results: dict[str, dict] = {}


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    suffix = f" ({detail})" if detail and not condition else ""
    print(f"    [{status}] {label}{suffix}")
    return condition


def run_wiktionary(lang: str, word: str) -> bool:
    data = wiktionary.fetch(word, lang)
    if data is None:
        print(f"    [FAIL] returned None")
        return False
    ok = True
    ok &= check("has ipa",     bool(data.get("ipa")),     f"got: {data.get('ipa')}")
    ok &= check("has entries", bool(data.get("entries")), f"got: {data.get('entries')}")
    if data.get("entries"):
        pos_list = [e["pos"] for e in data["entries"]]
        ok &= check("has at least one POS", bool(pos_list), f"got: {pos_list}")
        ok &= check("has at least one definition",
                    any(e["definitions"] for e in data["entries"]))
    return ok


def run_reverso(lang: str, word: str) -> bool:
    examples = reverso.fetch(word, lang, limit=3)
    if examples is None:
        print(f"    [FAIL] returned None")
        return False
    ok = True
    ok &= check("returned a list",           isinstance(examples, list))
    ok &= check("at least 1 example",        len(examples) >= 1, f"got {len(examples)}")
    ok &= check("limit respected",           len(examples) <= 3, f"got {len(examples)}")
    ok &= check("examples have source",      all("source" in e for e in examples))
    ok &= check("examples have translation", all("translation" in e for e in examples))
    ok &= check("sources non-empty",         all(e["source"].strip() for e in examples))
    ok &= check("translations non-empty",    all(e["translation"].strip() for e in examples))
    return ok


total_pass = 0
total_fail = 0

for lang, word in TEST_WORDS.items():
    print(f"\n{SEP}")
    print(f"{lang}  '{word}'")
    print(SEP)

    print("  Wiktionary:")
    wikt_ok = run_wiktionary(lang, word)

    print("  Reverso:")
    rev_ok = run_reverso(lang, word)

    results[lang] = {"wikt": wikt_ok, "reverso": rev_ok}
    total_pass += wikt_ok + rev_ok
    total_fail += (not wikt_ok) + (not rev_ok)

print(f"\n{SEP}")
print(f"SUMMARY  —  {total_pass} passed, {total_fail} failed")
print(SEP)
print(f"{'LANG':<6}  {'WIKTIONARY':<12}  {'REVERSO'}")
print(f"{'─'*6}  {'─'*12}  {'─'*12}")
for lang, r in results.items():
    w = "PASS" if r["wikt"] else "FAIL"
    v = "PASS" if r["reverso"] else "FAIL"
    print(f"{lang:<6}  {w:<12}  {v}")
print()
