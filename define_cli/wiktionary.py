"""Scrape IPA, POS, and definitions from English Wiktionary."""

from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup, Tag

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

LANG_SECTION_NAMES = {
    "ar": "Arabic",
    "ca": "Catalan",
    "zh": "Chinese",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "fa": "Persian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "es": "Spanish",
    "sv": "Swedish",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
}

POS_TAGS = {
    # Core
    "Noun", "Verb", "Adjective", "Adverb", "Preposition",
    "Conjunction", "Interjection", "Pronoun", "Article",
    "Determiner", "Numeral", "Particle", "Suffix", "Prefix",
    "Participle",
    # Extended
    "Proper noun", "Phrase", "Idiom", "Proverb", "Abbreviation",
    "Contraction", "Symbol", "Letter", "Punctuation mark",
    "Number", "Romanization", "Han character", "Affix",
    "Circumfix", "Infix", "Interfix", "Clitic",
    "Postposition", "Prepositional phrase",
}

NATIVE_WIKT_LANGS = {
    "ar": "ar", "ca": "ca", "zh": "zh", "cs": "cs", "da": "da",
    "nl": "nl", "fr": "fr", "de": "de", "el": "el", "he": "he",
    "hi": "hi", "hu": "hu", "it": "it", "ja": "ja", "ko": "ko",
    "fa": "fa", "pl": "pl", "pt": "pt", "ro": "ro", "ru": "ru",
    "sk": "sk", "es": "es", "sv": "sv", "th": "th", "tr": "tr",
    "uk": "uk", "vi": "vi",
}

LATIN_SCRIPT_LANGS = {
    "fr", "nl", "de", "es", "it", "pt", "ca", "cs", "da",
    "hu", "pl", "ro", "sk", "sv", "tr", "vi",
}


# ---------------------------------------------------------------------------
# Native IPA extractors — one callable per language.
# Each receives a BeautifulSoup object and returns list[str].
# Breakage in one language is isolated to its own function.
# ---------------------------------------------------------------------------

def _ipa_span_classes(soup: BeautifulSoup, *classes: str) -> list[str]:
    """Generic: collect IPA text from spans whose class is in `classes`."""
    results: list[str] = []
    for span in soup.find_all("span", class_=list(classes)):
        text = span.get_text(strip=True)
        if text and text not in results and _looks_like_ipa(text):
            results.append(text)
    return results


def _ipa_native_default(soup: BeautifulSoup) -> list[str]:
    return _ipa_span_classes(soup, "IPA")


def _ipa_native_ipa_lower(soup: BeautifulSoup) -> list[str]:
    return _ipa_span_classes(soup, "ipa")


def _ipa_native_ipAtekst(soup: BeautifulSoup) -> list[str]:
    return _ipa_span_classes(soup, "IPAtekst")


def _ipa_native_fr(soup: BeautifulSoup) -> list[str]:
    return _ipa_span_classes(soup, "API", "audio-ipa")


def _ipa_native_uk(soup: BeautifulSoup) -> list[str]:
    results: list[str] = []
    for font in soup.find_all("font"):
        text = font.get_text(strip=True)
        if text and text not in results and _looks_like_ipa(text):
            results.append(text)
    return results


def _ipa_native_es(soup: BeautifulSoup) -> list[str]:
    results: list[str] = []
    for table in soup.find_all("table", class_="pron-graf"):
        for td in table.find_all("td"):
            text = td.get_text(strip=True)
            if _looks_like_ipa(text):
                match = re.search(r'[/\[]([\w\s\u02b0-\u036f\u0250-\u02af]+)[/\]]', text)
                if match:
                    candidate = f"/{match.group(1)}/" if "/" in text else f"[{match.group(1)}]"
                    if candidate not in results:
                        results.append(candidate)
                        break
        if results:
            break
    return results


def _ipa_native_el(soup: BeautifulSoup) -> list[str]:
    results: list[str] = []
    for dd in soup.find_all("dd"):
        text = dd.get_text(strip=True)
        if "ΔΦΑ" in text and _looks_like_ipa(text):
            match = re.search(r'[/\[]([^/\]]+)[/\]]', text)
            if match:
                results.append(f"/{match.group(1)}/")
                break
    return results


def _ipa_native_fa(soup: BeautifulSoup) -> list[str]:
    results: list[str] = []
    for section in soup.find_all("section"):
        text = section.get_text(strip=True)
        match = re.search(r'/([^/]+)/', text)
        if match and _looks_like_ipa(f"/{match.group(1)}/"):
            results.append(f"/{match.group(1)}/")
            break
    return results


def _ipa_native_ro(soup: BeautifulSoup) -> list[str]:
    results: list[str] = []
    for section in soup.find_all("section"):
        text = section.get_text(strip=True)
        if "AFI" in text:
            match = re.search(r"[/'\u02c8]([^/'\u02c8\s]+)", text)
            if match:
                full = re.search(r"/[^/]+/|'\S+'", text)
                if full:
                    results.append(full.group(0))
                    break
    return results


_NATIVE_IPA_EXTRACTORS: dict[str, list] = {
    "ar": [_ipa_native_default],
    "ca": [_ipa_native_default],
    "zh": [_ipa_native_default],
    "cs": [_ipa_native_default],
    "da": [_ipa_native_default],
    "it": [_ipa_native_default],
    "ja": [_ipa_native_default],
    "ko": [_ipa_native_default],
    "th": [_ipa_native_default],
    "vi": [_ipa_native_default],
    "hu": [_ipa_native_default],
    "sk": [_ipa_native_default],
    "tr": [_ipa_native_default],
    "pt": [_ipa_native_ipa_lower],
    "pl": [_ipa_native_ipa_lower],
    "de": [_ipa_native_ipa_lower],
    "ru": [_ipa_native_ipa_lower],
    "nl": [_ipa_native_ipAtekst],
    "sv": [_ipa_native_ipAtekst],
    "fr": [_ipa_native_fr],
    "uk": [_ipa_native_uk],
    "es": [_ipa_native_es],
    "el": [_ipa_native_el],
    "fa": [_ipa_native_fa],
    "ro": [_ipa_native_ro],
    "he": [],
    "hi": [],
}


def _heading_id(tag: Tag) -> str | None:
    tag_id = tag.get("id", "")
    if tag_id:
        return re.sub(r"_\d+$", "", tag_id)
    inner = tag.find(["h2", "h3", "h4"])
    if inner:
        inner_id = inner.get("id", "")
        if inner_id:
            return re.sub(r"_\d+$", "", inner_id)
    span = tag.find("span", class_="mw-headline")
    if span:
        return span.get_text(strip=True)
    return None


def _is_lang_heading(tag: Tag) -> bool:
    if tag.name == "div" and "mw-heading2" in tag.get("class", []):
        return True
    if tag.name == "h2":
        return bool(tag.get("id"))
    return False


def _find_lang_container(soup: BeautifulSoup, lang_name: str) -> Tag | None:
    for tag in soup.find_all(["h2", "div"]):
        if tag.name == "div" and "mw-heading2" not in tag.get("class", []):
            continue
        if _heading_id(tag) == lang_name:
            return tag
    return None


def _fetch_soup(word: str) -> tuple[BeautifulSoup | None, bool]:
    """Returns (soup, network_ok). network_ok=False only on exception, not 404."""
    url = f"https://en.wiktionary.org/wiki/{requests.utils.quote(word)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml"), True
        return None, True  # 404 or other HTTP error — server reached, word not found
    except Exception:
        return None, False  # genuine network failure


def _looks_like_ipa(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if re.search(r'[ˈˌ]', t):
        return True
    if re.search(r'^[/\[\\]', t) or re.search(r'[/\]\\]$', t):
        if re.search(r'Prononciation|Pronunciation|\?', t):
            return False
        return True
    return False


def _fetch_ipa_native(word: str, lang: str) -> list[str]:
    extractors = _NATIVE_IPA_EXTRACTORS.get(lang, [])
    if not extractors:
        return []
    url = f"https://{lang}.wiktionary.org/wiki/{requests.utils.quote(word)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
    except Exception:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    for extractor in extractors:
        results = extractor(soup)
        if results:
            return results
    return []


def fetch(word: str, lang: str) -> dict:
    """
    Returns one of:
      {"status": "ok", "ipa": [...], "entries": [...], "actual_word": "..."}
      {"status": "not_found"}
      {"status": "network_error"}
    """
    lang_name = LANG_SECTION_NAMES.get(lang)
    if not lang_name:
        return {"status": "not_found"}

    variants = [word]
    if lang in LATIN_SCRIPT_LANGS:
        lower = word.lower()
        title = word.lower().title()
        if lower != word:
            variants.append(lower)
        if title not in variants:
            variants.append(title)

    any_network_success = False
    soup = None
    actual_word = word
    lang_container = None

    for variant in variants:
        s, network_ok = _fetch_soup(variant)
        if network_ok:
            any_network_success = True
        if s is None:
            continue
        lc = _find_lang_container(s, lang_name)
        if lc is not None:
            soup = s
            lang_container = lc
            actual_word = variant
            break

    if lang_container is None:
        if not any_network_success:
            return {"status": "network_error"}
        return {"status": "not_found"}


    if lang_container is None:
        if network_failed:
            return {"status": "network_error"}
        return {"status": "not_found"}

    # Collect siblings until the next language-level heading
    section_nodes: list[Tag] = []
    for sib in lang_container.next_siblings:
        if isinstance(sib, Tag):
            if _is_lang_heading(sib):
                break
            section_nodes.append(sib)

    # --- IPA ---
    ipa_list: list[str] = []
    for node in section_nodes:
        for span in node.find_all("span", class_="IPA"):
            text = span.get_text(strip=True)
            if text and text not in ipa_list and _looks_like_ipa(text):
                ipa_list.append(text)

    if not ipa_list and lang in NATIVE_WIKT_LANGS:
        ipa_list = _fetch_ipa_native(actual_word, lang)

    # --- POS + definitions ---
    entries: list[dict] = []
    current_pos: str | None = None

    for node in section_nodes:
        if node.name in ("h3", "h4"):
            heading = _heading_id(node)
            if heading:
                current_pos = heading
        elif node.name == "div" and any(
            c in node.get("class", []) for c in ("mw-heading3", "mw-heading4")
        ):
            h = node.find(["h3", "h4"])
            if h:
                heading = _heading_id(h)
                if heading:
                    current_pos = heading

        if node.name == "ol" and current_pos:
            defs: list[str] = []
            for li in node.find_all("li", recursive=False):
                for sub in li.find_all(["dl", "ul"]):
                    sub.decompose()
                for span in li.find_all("span", class_=["qualifier-brac", "ib-brac", "ib-content"]):
                    span.decompose()
                text = li.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)
                text = re.sub(r"\( ", "(", text)
                text = re.sub(r" \)", ")", text)
                text = re.sub(r" ([,;])", r"\1", text)
                text = re.sub(r"\s*\[\d+[–\-][^\]]*\]\s*", " ", text)
                text = text.strip()
                if text:
                    defs.append(text)
            if defs:
                if entries and entries[-1]["pos"] == current_pos:
                    entries[-1]["definitions"].extend(defs)
                else:
                    entries.append({"pos": current_pos, "definitions": defs})

    # Invariant assertions — fail loud if structure is wrong
    assert isinstance(ipa_list, list), "ipa_list must be a list"
    assert all(isinstance(s, str) for s in ipa_list), "all IPA entries must be strings"
    assert isinstance(entries, list), "entries must be a list"
    assert all(isinstance(e, dict) for e in entries), "each entry must be a dict"
    assert all("pos" in e and "definitions" in e for e in entries), \
        "each entry must have 'pos' and 'definitions'"
    assert all(isinstance(e["pos"], str) for e in entries), "pos must be a string"
    assert all(
        isinstance(e["definitions"], list) and
        all(isinstance(d, str) for d in e["definitions"])
        for e in entries
    ), "definitions must be a list of strings"

    return {"status": "ok", "ipa": ipa_list, "entries": entries, "actual_word": actual_word}
