"""Tests for CLI argument parsing in main.py."""

import pytest
from unittest.mock import patch, MagicMock
from define_cli.main import build_parser, main


# ── Parser unit tests ────────────────────────────────────────────────────────

class TestParser:
    def setup_method(self):
        self.parser = build_parser()

    def test_basic_parse(self):
        args = self.parser.parse_args(["fr", "bonjour"])
        assert args.lang == "fr"
        assert args.word == "bonjour"
        assert not args.examples
        assert not args.no_defs
        assert not args.no_examples

    def test_examples_short_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "-e"])
        assert args.examples is True

    def test_examples_long_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "--examples"])
        assert args.examples is True

    def test_no_defs_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "--no-defs"])
        assert args.no_defs is True

    def test_no_examples_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "--no-examples"])
        assert args.no_examples is True

    def test_dutch_word(self):
        args = self.parser.parse_args(["nl", "ingewikkeld"])
        assert args.lang == "nl"
        assert args.word == "ingewikkeld"

    def test_missing_word_raises(self):
        with patch("sys.argv", ["define", "fr"]):
            with pytest.raises(SystemExit):
                main()

    def test_missing_lang_raises(self):
        with patch("sys.argv", ["define"]):
            with pytest.raises(SystemExit):
                main()

    def test_flags_can_combine(self):
        args = self.parser.parse_args(["fr", "bonjour", "--no-defs", "--no-examples"])
        assert args.no_defs is True
        assert args.no_examples is True


# ── main() integration (mocked fetchers) ────────────────────────────────────

MOCK_WIKT = {
    "ipa": ["/bɔ̃.ʒuʁ/"],
    "entries": [
        {"pos": "Interjection", "definitions": ["hello, good morning"]}
    ],
}

MOCK_REVERSO = [
    {"source": "Bonjour, comment allez-vous ?", "translation": "Hello, how are you?"},
    {"source": "Il lui a dit bonjour.", "translation": "He said hello to her."},
]


class TestMainIntegration:
    def _run(self, argv):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("define_cli.main.reverso.fetch", return_value=MOCK_REVERSO), \
             patch("sys.argv", ["define"] + argv):
            main()

    def test_normal_lookup_runs(self, capsys):
        self._run(["fr", "bonjour"])
        out = capsys.readouterr().out
        assert "bonjour" in out.lower()

    def test_ipa_in_output(self, capsys):
        self._run(["fr", "bonjour"])
        out = capsys.readouterr().out
        assert "/bɔ̃.ʒuʁ/" in out

    def test_pos_in_output(self, capsys):
        self._run(["fr", "bonjour"])
        out = capsys.readouterr().out
        assert "interjection" in out.lower()

    def test_definition_in_output(self, capsys):
        self._run(["fr", "bonjour"])
        out = capsys.readouterr().out
        assert "hello" in out.lower()

    def test_example_source_in_output(self, capsys):
        self._run(["fr", "bonjour"])
        out = capsys.readouterr().out
        assert "Bonjour, comment allez-vous" in out

    def test_invalid_lang_exits(self):
        with patch("sys.argv", ["define", "xx", "bonjour"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    def test_no_defs_skips_wiktionary(self):
        with patch("define_cli.main.wiktionary.fetch") as mock_wikt, \
             patch("define_cli.main.reverso.fetch", return_value=MOCK_REVERSO), \
             patch("sys.argv", ["define", "fr", "bonjour", "--no-defs"]):
            main()
            mock_wikt.assert_not_called()

    def test_no_examples_skips_reverso(self):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("define_cli.main.reverso.fetch") as mock_reverso, \
             patch("sys.argv", ["define", "fr", "bonjour", "--no-examples"]):
            main()
            mock_reverso.assert_not_called()

    def test_examples_flag_passes_none_limit(self):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("define_cli.main.reverso.fetch", return_value=MOCK_REVERSO) as mock_reverso, \
             patch("sys.argv", ["define", "fr", "bonjour", "-e"]):
            main()
            call_kwargs = mock_reverso.call_args
            # limit arg is positional index 2
            assert call_kwargs.args[2] is None or call_kwargs.kwargs.get("limit") is None

class TestLangsFlag:
    def test_langs_flag_exits_cleanly(self):
        with patch("sys.argv", ["define", "--langs"]):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None

    def test_langs_output_contains_french(self, capsys):
        with patch("sys.argv", ["define", "--langs"]):
            try:
                main()
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert "French" in out
        assert "fr" in out

    def test_langs_output_contains_all_codes(self, capsys):
        with patch("sys.argv", ["define", "--langs"]):
            try:
                main()
            except SystemExit:
                pass
        out = capsys.readouterr().out
        for code in ["ar", "ca", "zh", "cs", "da", "nl", "fr", "de", "el",
                     "he", "hi", "hu", "it", "ja", "ko", "fa", "pl", "pt",
                     "ro", "ru", "sk", "es", "sv", "th", "tr", "uk", "vi"]:
            assert code in out, f"Missing language code: {code}"

    def test_no_args_exits_with_error(self):
        with patch("sys.argv", ["define"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code != 0

    def test_lang_without_word_exits_with_error(self):
        with patch("sys.argv", ["define", "fr"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code != 0
