"""Tests for reverso.py parser using HTML fixtures."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from define_cli import reverso

FIXTURES = Path(__file__).parent / "fixtures"

MOCK_REVERSO = {
    "status": "ok",
    "examples": [
        {"source": "Bonjour, comment allez-vous ?", "translation": "Hello, how are you?"},
        {"source": "Il lui a dit bonjour.", "translation": "He said hello to her."},
    ],
}

def _mock_get(fixture_file, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.text = (FIXTURES / fixture_file).read_text(encoding="utf-8")
    return resp


class TestBonjour:
    @pytest.fixture(autouse=True)
    def mock_request(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            self.result_default = reverso.fetch("bonjour", "fr", limit=5)

    def test_returns_dict(self):
        assert isinstance(self.result_default, dict)
        assert self.result_default["status"] == "ok"

    def test_returns_examples_list(self):
        assert isinstance(self.result_default["examples"], list)

    def test_default_limit_respected(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=5)
        assert len(result["examples"]) == 5

    def test_no_limit_returns_all(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=None)
        assert len(result["examples"]) == 6

    def test_limit_of_one(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_bonjour.html")):
            result = reverso.fetch("bonjour", "fr", limit=1)
        assert len(result["examples"]) == 1

    def test_example_has_source_and_translation(self):
        ex = self.result_default["examples"][0]
        assert "source" in ex
        assert "translation" in ex

    def test_source_is_nonempty_string(self):
        for ex in self.result_default["examples"]:
            assert isinstance(ex["source"], str) and ex["source"]

    def test_translation_is_nonempty_string(self):
        for ex in self.result_default["examples"]:
            assert isinstance(ex["translation"], str) and ex["translation"]

    def test_source_is_french(self):
        sources = [ex["source"] for ex in self.result_default["examples"]]
        assert any("bonjour" in s.lower() for s in sources)

    def test_translation_is_english(self):
        translations = [ex["translation"] for ex in self.result_default["examples"]]
        assert any("hello" in t.lower() or "good morning" in t.lower() for t in translations)


class TestMissing:
    def test_returns_not_found_when_no_examples(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_missing.html")):
            result = reverso.fetch("zzznonsense", "fr")
        assert result["status"] == "not_found"

    def test_returns_not_found_on_http_error(self):
        with patch("define_cli.reverso.cf_requests.get",
                   return_value=_mock_get("reverso_missing.html", status=404)):
            result = reverso.fetch("zzznonsense", "fr")
        assert result["status"] in ("not_found", "network_error")

    def test_returns_unsupported_for_unknown_lang(self):
        result = reverso.fetch("bonjour", "xx")
        assert result["status"] == "unsupported"
