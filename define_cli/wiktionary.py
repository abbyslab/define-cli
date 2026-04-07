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
    "Noun", "Verb", "Adjective", "Adverb", "Preposition",
    "Conjunction", "Interjection", "Pronoun", "Article",
    "Determiner", "Numeral", "Particle", "Suffix", "Prefix",
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


def _heading_id(tag: Tag) -> str | None:
    """Extract normalised heading id from any known Wiktionary heading structure."""
    # 1. id directly on tag (new style bare h2/h3)
    tag_id = tag.get("id", "")
    if tag_id:
        return re.sub(r"_\d+$", "", tag_id)
    # 2. id on inner h2/h3/h4 (new style div.mw-heading wrapping)
    inner = tag.find(["h2", "h3", "h4"])
    if inner:
        inner_id = inner.get("id", "")
        if inner_id:
            return re.sub(r"_\d+$", "", inner_id)
    # 3. old style mw-headline span
    span = tag.find("span", class_="mw-headline")
    if span:
        return span.get_text(strip=True)
    return None


def _is_lang_heading(tag: Tag) -> bool:
    """True if tag marks the start of a new language section."""
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


def _fetch_soup(word: str) -> BeautifulSoup | None:
    url = f"https://en.wiktionary.org/wiki/{requests.utils.quote(word)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None

def _looks_like_ipa(text: str) -> bool:
    t = text.strip()
    # Has stress marks — accept regardless
    if re.search(r'[ˈˌ]', t):
        return True
    # Has /.../ or [...] delimiters — accept if not obviously a non-IPA label
    if re.search(r'^[/\[\\]', t) or re.search(r'[/\]\\]$', t):
        # Reject known placeholder patterns
        if re.search(r'Prononciation|Pronunciation|\?', t):
            return False
        return True
    return False

def _fetch_ipa_native(word: str, lang: str) -> list[str]:
    url = f"https://{lang}.wiktionary.org/wiki/{requests.utils.quote(word)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    ipa_list: list[str] = []

    # Standard span-based IPA
    for span in soup.find_all("span", class_=["IPA", "ipa", "IPAtekst", "API", "audio-ipa"]):
        text = span.get_text(strip=True)
        if text and text not in ipa_list and _looks_like_ipa(text):
            ipa_list.append(text)

    # Font-tag based IPA (Ukrainian)
    if not ipa_list:
        for font in soup.find_all("font"):
            text = font.get_text(strip=True)
            if text and text not in ipa_list and _looks_like_ipa(text):
                ipa_list.append(text)

    # Spanish: IPA in td inside pron-graf tables
    if not ipa_list and lang == "es":
        for table in soup.find_all("table", class_="pron-graf"):
            for td in table.find_all("td"):
                text = td.get_text(strip=True)
                if _looks_like_ipa(text):
                    # extract just the IPA part
                    match = re.search(r'[/\[]([\w\s\u02b0-\u036f\u0250-\u02af]+)[/\]]', text)
                    if match:
                        candidate = f"/{match.group(1)}/" if "/" in text else f"[{match.group(1)}]"
                        if candidate not in ipa_list:
                            ipa_list.append(candidate)
                            break
            if ipa_list:
                break

    # Greek: IPA in dd tags containing ΔΦΑ:
    if not ipa_list and lang == "el":
        for dd in soup.find_all("dd"):
            text = dd.get_text(strip=True)
            if "ΔΦΑ" in text and _looks_like_ipa(text):
                match = re.search(r'[/\[]([^/\]]+)[/\]]', text)
                if match:
                    ipa_list.append(f"/{match.group(1)}/")
                    break

    # Persian: IPA in section text as /word/
    if not ipa_list and lang == "fa":
        for section in soup.find_all("section"):
            text = section.get_text(strip=True)
            match = re.search(r'/([^/]+)/', text)
            if match and _looks_like_ipa(f"/{match.group(1)}/"):
                ipa_list.append(f"/{match.group(1)}/")
                break

    # Romanian: IPA in span inside section with AFI:
    if not ipa_list and lang == "ro":
        for section in soup.find_all("section"):
            text = section.get_text(strip=True)
            if "AFI" in text:
                match = re.search(r"[/'\u02c8]([^/'\u02c8\s]+)", text)
                if match:
                    full = re.search(r"/[^/]+/|'\S+'", text)
                    if full:
                        ipa_list.append(full.group(0))
                        break

    return ipa_list

def fetch(word: str, lang: str) -> dict | None:
    lang_name = LANG_SECTION_NAMES.get(lang)
    if not lang_name:
        return None

    # Build list of word variants to try, in order
    variants = [word]
    if lang in LATIN_SCRIPT_LANGS:
        lower = word.lower()
        title = word.lower().title()
        if lower != word:
            variants.append(lower)
        if title not in variants:
            variants.append(title)

    soup = None
    actual_word = word
    lang_container = None

    for variant in variants:
        soup = _fetch_soup(variant)
        if soup is None:
            continue
        lang_container = _find_lang_container(soup, lang_name)
        if lang_container is not None:
            actual_word = variant
            break

    if lang_container is None or soup is None:
        return None

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

    # IPA fallback: try native-language Wiktionary if EN gave nothing
    if not ipa_list and lang in NATIVE_WIKT_LANGS:
        ipa_list = _fetch_ipa_native(actual_word, lang)

    # --- POS + definitions ---
    entries: list[dict] = []
    current_pos: str | None = None

    for node in section_nodes:
        if node.name in ("h3", "h4"):
            heading = _heading_id(node)
            if heading in POS_TAGS:
                current_pos = heading
        elif node.name == "div" and any(
            c in node.get("class", []) for c in ("mw-heading3", "mw-heading4")
        ):
            h = node.find(["h3", "h4"])
            if h:
                heading = _heading_id(h)
                if heading in POS_TAGS:
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

    return {"ipa": ipa_list, "entries": entries, "actual_word": actual_word}
