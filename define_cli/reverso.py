"""Scrape usage examples from Reverso Context, with Tatoeba fallback."""

from __future__ import annotations
import requests as std_requests
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup

import re

def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ([,;:.!?»)\]])", r"\1", text)
    text = re.sub(r"([(«\[]) ", r"\1", text)
    text = re.sub(r'" ([^"]+) "', r'"\1"', text)
    # collapse spaces around single CJK/Arabic/Hebrew characters
    text = re.sub(r" ([\u0600-\u06ff\u0590-\u05ff\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]) ", r"\1", text)
    return text.strip()

HEADERS = {
    "Accept-Language": "en-GB,en;q=0.9",
}

# Languages Reverso supports for X→English
REVERSO_LANGS = {
    "ar": "arabic",
    "zh": "chinese",
    "nl": "dutch",
    "fr": "french",
    "de": "german",
    "he": "hebrew",
    "it": "italian",
    "ja": "japanese",
    "ko": "korean",
    "pl": "polish",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "es": "spanish",
    "sv": "swedish",
    "tr": "turkish",
    "uk": "ukrainian",
}

# ISO 639-3 codes for Tatoeba API
TATOEBA_LANGS = {
    "ar": "ara",
    "ca": "cat",
    "zh": "cmn",
    "cs": "ces",
    "da": "dan",
    "nl": "nld",
    "fr": "fra",
    "de": "deu",
    "el": "ell",
    "he": "heb",
    "hi": "hin",
    "hu": "hun",
    "it": "ita",
    "ja": "jpn",
    "ko": "kor",
    "fa": "fas",
    "pl": "pol",
    "pt": "por",
    "ro": "ron",
    "ru": "rus",
    "sk": "slk",
    "es": "spa",
    "sv": "swe",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "vi": "vie",
}


def _fetch_reverso(word: str, lang: str, limit: int | None) -> list[dict] | None:
    lang_name = REVERSO_LANGS.get(lang)
    if not lang_name:
        return None

    url = (
        f"https://context.reverso.net/translation/"
        f"{lang_name}-english/{cf_requests.utils.quote(word)}"
    )
    resp = cf_requests.get(url, headers=HEADERS, impersonate="chrome", timeout=15)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    examples: list[dict] = []

    for ex in soup.find_all("div", class_="example"):
        src_el = ex.find("div", class_="src")
        trg_el = ex.find("div", class_="trg")
        if not src_el or not trg_el:
            continue
        src_text = _clean(src_el.get_text(separator=" ", strip=True))
        trg_text = _clean(trg_el.get_text(separator=" ", strip=True))
        if src_text and trg_text:
            examples.append({"source": src_text, "translation": trg_text})
        if limit is not None and len(examples) >= limit:
            break

    return examples if examples else None


def _fetch_tatoeba(word: str, lang: str, limit: int | None) -> list[dict] | None:
    lang3 = TATOEBA_LANGS.get(lang)
    if not lang3:
        return None

    params = {
        "from": lang3,
        "to": "eng",
        "query": word,
        "limit": min(limit or 10, 10),
        "orphans": "no",
        "unapproved": "no",
    }
    try:
        resp = std_requests.get(
            "https://tatoeba.org/en/api_v0/search",
            params=params,
            timeout=10,
            headers={"User-Agent": "define-cli/0.1"},
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    examples: list[dict] = []
    for result in data.get("results", []):
        src_text = result.get("text", "").strip()
        translations = result.get("translations", [])
        # translations is a list of lists
        trg_text = ""
        for group in translations:
            for t in group:
                if t.get("lang") == "eng" and t.get("text"):
                    trg_text = t["text"].strip()
                    break
            if trg_text:
                break

        if src_text and trg_text:
            examples.append({"source": src_text, "translation": trg_text})

        if limit is not None and len(examples) >= limit:
            break

    return examples if examples else None


def fetch(word: str, lang: str, limit: int | None = 5) -> list[dict] | None:
    """Try Reverso first, fall back to Tatoeba."""
    result = _fetch_reverso(word, lang, limit)
    if result:
        return result
    return _fetch_tatoeba(word, lang, limit)
