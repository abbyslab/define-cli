"""Tests for wiktionary.py parser using HTML fixtures."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from define_cli import wiktionary

FIXTURES = Path(__file__).parent / "fixtures"

MOCK_WIKT = {
    "ipa": ["/bɔ̃.ʒuʁ/"],
    "entries": [{"pos": "Interjection", "definitions": ["hello, good morning"]}],
    "actual_word": "bonjour",
}

def _mock_get(fixture_file, status=200):
    """Return a mock requests.Response backed by a fixture file."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = (FIXTURES / fixture_file).read_text(encoding="utf-8")
    return resp

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

class TestUnsupportedLang:
    def test_returns_none_for_unknown_lang(self):
        result = wiktionary.fetch("bonjour", "xx")
        assert result is None

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

class TestPOSTags:
    def test_participle_is_recognised(self):
        """'Participle' must be in POS_TAGS so past participles get definitions."""
        assert "Participle" in wiktionary.POS_TAGS

class TestLooksLikeIPA:
    def test_rejects_rhyme_notation(self):
        assert not wiktionary._looks_like_ipa("-oːpt")

    def test_rejects_prononciation_placeholder(self):
        assert not wiktionary._looks_like_ipa("[Prononciation?]")

    def test_accepts_slash_delimited(self):
        assert wiktionary._looks_like_ipa("/bɔ̃.ʒuʁ/")

    def test_accepts_bracket_delimited_with_ipa_chars(self):
        assert wiktionary._looks_like_ipa("[ɡəlaufn̩]")

    def test_accepts_stress_marked(self):
        assert wiktionary._looks_like_ipa("ˈʃmɛtɐˌlɪŋə")

    def test_accepts_backslash_delimited(self):
        assert wiktionary._looks_like_ipa("\\ʃɑ̃.tjɔ̃\\")

    def test_rejects_plain_word(self):
        assert not wiktionary._looks_like_ipa("loopt")

class TestLooksLikeIPAAdversarial:
    def test_single_char_slash_delimited(self):
        assert wiktionary._looks_like_ipa("/a/")

    def test_double_slash_empty(self):
        # // has delimiters but no content — could go either way
        # we just care it doesn't crash
        result = wiktionary._looks_like_ipa("//")
        assert isinstance(result, bool)

    def test_slash_latin_word(self):
        # /hello/ has delimiters but no IPA chars — currently accepted
        # document current behaviour
        assert wiktionary._looks_like_ipa("/hello/") is True

    def test_repeated_stress_marks(self):
        assert wiktionary._looks_like_ipa("ˈˈˈ") is True

    def test_length_mark_only(self):
        # aːb has length mark but no stress/delimiter
        assert not wiktionary._looks_like_ipa("aːb")

    def test_mixed_valid(self):
        assert wiktionary._looks_like_ipa("/ˈbɔ̃.ʒuʁ/")

    def test_empty_string(self):
        assert not wiktionary._looks_like_ipa("")

    def test_whitespace_only(self):
        assert not wiktionary._looks_like_ipa("   ")

    def test_number_string(self):
        assert not wiktionary._looks_like_ipa("12345")

    def test_punctuation_only(self):
        assert not wiktionary._looks_like_ipa(".,;:!?")


class TestUnknownPOS:
    def test_unknown_pos_heading_is_skipped(self):
        """A POS heading not in POS_TAGS should produce no entries."""
        html = """<html><body>
            <div class="mw-heading mw-heading2"><h2 id="French">French</h2></div>
            <div class="mw-heading mw-heading3"><h3 id="Proverb">Proverb</h3></div>
            <ol><li>some proverb definition</li></ol>
        </body></html>"""
        from unittest.mock import patch, MagicMock
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.status_code = 200
            r.text = html
            return r
        with patch("define_cli.wiktionary.requests.get", side_effect=mock_get):
            result = wiktionary.fetch("quelque", "fr")
        # Should return a result dict but with no entries
        assert result is not None
        assert result["entries"] == []

    def test_multiple_pos_blocks(self):
        """Multiple POS headings should each produce their own entry."""
        html = """<html><body>
            <div class="mw-heading mw-heading2"><h2 id="French">French</h2></div>
            <div class="mw-heading mw-heading3"><h3 id="Noun">Noun</h3></div>
            <ol><li>a thing</li></ol>
            <div class="mw-heading mw-heading3"><h3 id="Verb">Verb</h3></div>
            <ol><li>to do something</li></ol>
        </body></html>"""
        from unittest.mock import patch, MagicMock
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.status_code = 200
            r.text = html
            return r
        with patch("define_cli.wiktionary.requests.get", side_effect=mock_get):
            result = wiktionary.fetch("mot", "fr")
        assert result is not None
        pos_list = [e["pos"] for e in result["entries"]]
        assert "Noun" in pos_list
        assert "Verb" in pos_list


class TestRendererNoneCases:
    """Test render() directly with edge-case inputs."""

    def test_render_none_wikt_data(self, capsys):
        from define_cli import render
        render.render(
            word="test",
            lang="fr",
            wikt_data=None,
            reverso_data=None,
        )
        out = capsys.readouterr().out
        assert "pipx reinstall" in out

    def test_render_empty_ipa_list(self, capsys):
        from define_cli import render
        render.render(
            word="test",
            lang="fr",
            wikt_data={"ipa": [], "entries": [{"pos": "Noun", "definitions": ["thing"]}], "actual_word": "test"},
            reverso_data=None,
        )
        out = capsys.readouterr().out
        assert "thing" in out

    def test_render_none_reverso_shows_no_examples(self, capsys):
        from define_cli import render
        render.render(
            word="test",
            lang="fr",
            wikt_data=MOCK_WIKT,
            reverso_data=None,
        )
        out = capsys.readouterr().out
        assert "No examples found" in out

    def test_render_empty_reverso_list(self, capsys):
        from define_cli import render
        render.render(
            word="test",
            lang="fr",
            wikt_data=MOCK_WIKT,
            reverso_data=[],
        )
        out = capsys.readouterr().out
        assert "No examples found" in out
