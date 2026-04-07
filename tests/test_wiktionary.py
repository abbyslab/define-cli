"""Tests for wiktionary.py parser using HTML fixtures."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from define_cli import wiktionary

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_get(fixture_file, status=200):
    """Return a mock requests.Response backed by a fixture file."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = (FIXTURES / fixture_file).read_text(encoding="utf-8")
    return resp


# ── bonjour (French) ────────────────────────────────────────────────────────

class TestBonjour:
    @pytest.fixture(autouse=True)
    def mock_request(self):
        with patch("define_cli.wiktionary.requests.get",
                   return_value=_mock_get("wikt_bonjour.html")):
            self.result = wiktionary.fetch("bonjour", "fr")

    def test_returns_dict(self):
        assert isinstance(self.result, dict)

    def test_ipa_present(self):
        assert self.result["ipa"], "Expected at least one IPA entry"

    def test_ipa_correct(self):
        assert "/bɔ̃.ʒuʁ/" in self.result["ipa"]

    def test_ipa_deduplicated(self):
        assert len(self.result["ipa"]) == len(set(self.result["ipa"]))

    def test_entries_present(self):
        assert self.result["entries"], "Expected at least one POS entry"

    def test_interjection_present(self):
        pos_list = [e["pos"] for e in self.result["entries"]]
        assert "Interjection" in pos_list

    def test_noun_present(self):
        pos_list = [e["pos"] for e in self.result["entries"]]
        assert "Noun" in pos_list

    def test_interjection_definitions(self):
        entry = next(e for e in self.result["entries"] if e["pos"] == "Interjection")
        joined = " ".join(entry["definitions"]).lower()
        assert "hello" in joined or "good morning" in joined

    def test_nested_examples_stripped_from_defs(self):
        """Inline examples (dl/dd) should not appear in definition text."""
        for entry in self.result["entries"]:
            for defn in entry["definitions"]:
                assert "comment allez-vous" not in defn

    def test_occitan_section_excluded(self):
        """Content from the Occitan section should not leak in."""
        all_defs = [
            d for e in self.result["entries"] for d in e["definitions"]
        ]
        assert not any("Should not appear" in d for d in all_defs)

    def test_english_section_excluded(self):
        """English Wiktionary section for 'bonjour' should be ignored."""
        all_defs = [
            d for e in self.result["entries"] for d in e["definitions"]
        ]
        assert not any("borrowed from French" in d for d in all_defs)


# ── ingewikkeld (Dutch) ──────────────────────────────────────────────────────

class TestIngewikkeld:
    @pytest.fixture(autouse=True)
    def mock_request(self):
        with patch("define_cli.wiktionary.requests.get",
                   return_value=_mock_get("wikt_ingewikkeld.html")):
            self.result = wiktionary.fetch("ingewikkeld", "nl")

    def test_returns_dict(self):
        assert isinstance(self.result, dict)

    def test_ipa_correct(self):
        assert "/ˌɪŋ.əˈʋɪk.əlt/" in self.result["ipa"]

    def test_adjective_present(self):
        pos_list = [e["pos"] for e in self.result["entries"]]
        assert "Adjective" in pos_list

    def test_adjective_definition(self):
        entry = next(e for e in self.result["entries"] if e["pos"] == "Adjective")
        joined = " ".join(entry["definitions"]).lower()
        assert "complicated" in joined or "complex" in joined


# ── unsupported language ─────────────────────────────────────────────────────

class TestUnsupportedLang:
    def test_returns_none_for_unknown_lang(self):
        result = wiktionary.fetch("bonjour", "xx")
        assert result is None


# ── word not found ───────────────────────────────────────────────────────────

class TestMissingWord:
    def test_returns_none_when_no_section(self):
        with patch("define_cli.wiktionary.requests.get",
                   return_value=_mock_get("wikt_missing.html")):
            result = wiktionary.fetch("zzznonsense", "fr")
        assert result is None

    def test_returns_none_on_http_error(self):
        with patch("define_cli.wiktionary.requests.get",
                   return_value=_mock_get("wikt_missing.html", status=404)):
            result = wiktionary.fetch("zzznonsense", "fr")
        assert result is None


# ── lang mismatch ────────────────────────────────────────────────────────────

class TestLangMismatch:
    def test_returns_none_for_wrong_lang(self):
        """Fetching Dutch entry with fr lang should return None."""
        with patch("define_cli.wiktionary.requests.get",
                   return_value=_mock_get("wikt_ingewikkeld.html")):
            result = wiktionary.fetch("ingewikkeld", "fr")
        assert result is None

class TestNativeFallback:
    def test_dutch_inflected_form_gets_ipa(self):
        """loopt has no IPA on EN Wiktionary, so native nl.wiktionary fallback must fire."""
        from unittest.mock import patch, MagicMock
        from bs4 import BeautifulSoup

        # EN Wiktionary page with Dutch section but no IPA span
        en_html = """<html><body>
            <div class="mw-heading mw-heading2"><h2 id="Dutch">Dutch</h2></div>
            <div class="mw-heading mw-heading3"><h3 id="Verb">Verb</h3></div>
            <ol><li>inflection of lopen</li></ol>
        </body></html>"""

        # Native nl.wiktionary page with IPA
        nl_html = """<html><body>
            <span class="IPAtekst">/lopt/</span>
        </body></html>"""

        def mock_get(url, **kwargs):
            r = MagicMock()
            r.status_code = 200
            r.text = nl_html if "nl.wiktionary" in url else en_html
            return r

        with patch("define_cli.wiktionary.requests.get", side_effect=mock_get):
            result = wiktionary.fetch("loopt", "nl")

        assert result is not None
        assert result["ipa"] == ["/lopt/"]
