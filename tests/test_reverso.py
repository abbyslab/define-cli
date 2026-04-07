"""Tests for reverso.py parser using HTML fixtures."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from define_cli import reverso

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_get(fixture_file, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.text = (FIXTURES / fixture_file).read_text(encoding="utf-8")
    return resp


# ── bonjour (French) ────────────────────────────────────────────────────────

class TestBonjour:
    @pytest.fixture(autouse=True)
    def mock_request(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            self.result_default = reverso.fetch("bonjour", "fr", limit=5)
            self.result_all = reverso.fetch("bonjour", "fr", limit=None)

    # re-mock for all since fixture() doesn't re-run per method
    def test_returns_list(self):
        assert isinstance(self.result_default, list)

    def test_default_limit_respected(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=5)
        assert len(result) == 5

    def test_no_limit_returns_all(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=None)
        assert len(result) == 6  # fixture has 6 examples

    def test_limit_of_one(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=1)
        assert len(result) == 1

    def test_example_has_source_and_translation(self):
        ex = self.result_default[0]
        assert "source" in ex
        assert "translation" in ex

    def test_source_is_nonempty_string(self):
        for ex in self.result_default:
            assert isinstance(ex["source"], str)
            assert ex["source"].strip()

    def test_translation_is_nonempty_string(self):
        for ex in self.result_default:
            assert isinstance(ex["translation"], str)
            assert ex["translation"].strip()

    def test_source_is_french(self):
        sources = [ex["source"] for ex in self.result_default]
        assert any("bonjour" in s.lower() for s in sources)

    def test_translation_is_english(self):
        translations = [ex["translation"] for ex in self.result_default]
        assert any(
            "hello" in t.lower() or "good morning" in t.lower()
            for t in translations
        )


# ── missing / error cases ────────────────────────────────────────────────────

class TestMissing:
    def test_returns_none_when_no_examples(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_missing.html")):
            result = reverso.fetch("zzznonsense", "fr")
        assert result is None

    def test_returns_none_on_http_error(self):
        with patch("define_cli.reverso.requests.get",
                   return_value=_mock_get("reverso_missing.html", status=404)):
            result = reverso.fetch("zzznonsense", "fr")
        assert result is None

    def test_returns_none_for_unknown_lang(self):
        result = reverso.fetch("bonjour", "xx")
        assert result is None
