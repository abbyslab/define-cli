"""Tests for CLI argument parsing in main.py."""

import pytest
from unittest.mock import patch, MagicMock
from define_cli.main import build_parser, main
from define_cli import wiktionary

class TestParser:
    def setup_method(self):
        self.parser = build_parser()

    def test_basic_parse(self):
        args = self.parser.parse_args(["fr", "bonjour"])
        assert args.lang == "fr"
        assert args.word == "bonjour"
        assert not args.extended
        assert not args.no_defs
        assert not args.no_examples

    def test_examples_short_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "-e"])
        assert args.extended is True

    def test_examples_long_flag(self):
        args = self.parser.parse_args(["fr", "bonjour", "--extended"])
        assert args.extended is True

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

    def test_duplicate_flag_is_harmless(self):
        args = self.parser.parse_args(["fr", "bonjour", "--no-defs", "--no-defs"])
        assert args.no_defs is True

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
            assert call_kwargs.args[2] is None or call_kwargs.kwargs.get("limit") is None

    def test_extended_and_no_examples_combined(self):
        with patch("define_cli.main.reverso.fetch") as mock_reverso, \
             patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("sys.argv", ["define", "fr", "bonjour", "-e", "--no-examples"]):
            main()
            mock_reverso.assert_not_called()

    def test_langs_with_extra_args_still_works(self, capsys):
        with patch("sys.argv", ["define", "--langs", "fr"]):
            try:
                main()
            except SystemExit:
                pass
        out = capsys.readouterr().out
        assert "French" in out

    def test_empty_word_exits(self):
        with patch("sys.argv", ["define", "fr", ""]):
            with pytest.raises(SystemExit):
                main()

    def test_render_empty_entries_shows_reinstall_hint(self, capsys):
        empty_wikt = {"ipa": [], "entries": [], "actual_word": "xyz"}
        with patch("define_cli.main.wiktionary.fetch", return_value=empty_wikt), \
             patch("define_cli.main.reverso.fetch", return_value=None), \
             patch("sys.argv", ["define", "fr", "xyz"]):
            main()
        out = capsys.readouterr().out
        assert "pipx reinstall" in out

    def test_unknown_flag_exits(self):
        with patch("sys.argv", ["define", "fr", "bonjour", "--unknown-flag"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code != 0

    def test_shell_mode_without_lang_exits(self):
        with patch("sys.argv", ["define", "--shell"]):
            with pytest.raises(SystemExit):
                main()


class TestShellMode:
    def test_shell_mode_invalid_lang_exits(self):
        with patch("sys.argv", ["define", "--shell", "xx"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1


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


class TestRenderSkippedSources:
    def _run(self, argv, wikt=None, reverso=None):
        with patch("define_cli.main.wiktionary.fetch", return_value=wikt), \
             patch("define_cli.main.reverso.fetch", return_value=reverso), \
             patch("sys.argv", ["define"] + argv):
            main()

    def test_no_defs_flag_no_definitions_message(self, capsys):
        self._run(["fr", "bonjour", "--no-defs"], reverso=MOCK_REVERSO)
        out = capsys.readouterr().out
        assert "No definitions found" not in out

    def test_no_examples_flag_no_examples_message(self, capsys):
        self._run(["fr", "bonjour", "--no-examples"], wikt=MOCK_WIKT)
        out = capsys.readouterr().out
        assert "No examples found" not in out

    def test_no_results_hint_not_shown_when_sources_skipped(self, capsys):
        self._run(["fr", "bonjour", "--no-defs", "--no-examples"])
        out = capsys.readouterr().out
        assert "pipx reinstall" not in out

class TestWhitespaceWord:
    def test_whitespace_word_shows_no_results(self, capsys):
        with patch("sys.argv", ["define", "fr", " "]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    def test_newline_word_exits(self):
        with patch("sys.argv", ["define", "fr", "\n"]):
            with pytest.raises(SystemExit):
                main()

    def test_tab_word_exits(self):
        with patch("sys.argv", ["define", "fr", "\t"]):
            with pytest.raises(SystemExit):
                main()


class TestPartialScrapeResults:
    def test_ipa_only_no_entries(self, capsys):
        partial_wikt = {"ipa": ["/bɔ̃.ʒuʁ/"], "entries": [], "actual_word": "bonjour"}
        with patch("define_cli.main.wiktionary.fetch", return_value=partial_wikt), \
             patch("define_cli.main.reverso.fetch", return_value=None), \
             patch("sys.argv", ["define", "fr", "bonjour"]):
            main()
        out = capsys.readouterr().out
        assert "/bɔ̃.ʒuʁ/" in out
        assert "No definitions found" in out
        assert "No examples found" in out

    def test_entries_only_no_ipa(self, capsys):
        partial_wikt = {"ipa": [], "entries": [{"pos": "Noun", "definitions": ["hello"]}], "actual_word": "bonjour"}
        with patch("define_cli.main.wiktionary.fetch", return_value=partial_wikt), \
             patch("define_cli.main.reverso.fetch", return_value=None), \
             patch("sys.argv", ["define", "fr", "bonjour"]):
            main()
        out = capsys.readouterr().out
        assert "hello" in out

    def test_wikt_none_reverso_present(self, capsys):
        with patch("define_cli.main.wiktionary.fetch", return_value=None), \
             patch("define_cli.main.reverso.fetch", return_value=MOCK_REVERSO), \
             patch("sys.argv", ["define", "fr", "bonjour"]):
            main()
        out = capsys.readouterr().out
        assert "Bonjour, comment allez-vous" in out

    def test_both_none_shows_reinstall_hint(self, capsys):
        with patch("define_cli.main.wiktionary.fetch", return_value=None), \
             patch("define_cli.main.reverso.fetch", return_value=None), \
             patch("sys.argv", ["define", "fr", "bonjour"]):
            main()
        out = capsys.readouterr().out
        assert "pipx reinstall" in out

    def test_empty_examples_list(self, capsys):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("define_cli.main.reverso.fetch", return_value=None), \
             patch("sys.argv", ["define", "fr", "bonjour"]):
            main()
        out = capsys.readouterr().out
        assert "No examples found" in out


class TestShellModeLoop:
    def test_shell_eof_exits_cleanly(self):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("builtins.input", side_effect=EOFError), \
             patch("sys.argv", ["define", "--shell", "fr"]):
            main()  # should not raise

    def test_shell_keyboard_interrupt_exits_cleanly(self):
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("builtins.input", side_effect=KeyboardInterrupt), \
             patch("sys.argv", ["define", "--shell", "fr"]):
            main()  # should not raise

    def test_shell_empty_input_skipped(self):
        inputs = iter(["", "", EOFError()])
        def side_effect(prompt=""):
            val = next(inputs)
            if isinstance(val, BaseException):
                raise val
            return val
        with patch("define_cli.main.wiktionary.fetch", return_value=MOCK_WIKT), \
             patch("builtins.input", side_effect=side_effect), \
             patch("sys.argv", ["define", "--shell", "fr"]):
            main()  # should not call wiktionary.fetch for empty lines

    def test_shell_empty_input_does_not_fetch(self):
        inputs = iter(["", EOFError()])
        def side_effect(prompt=""):
            val = next(inputs)
            if isinstance(val, BaseException):
                raise val
            return val
        with patch("define_cli.main.wiktionary.fetch") as mock_wikt, \
             patch("builtins.input", side_effect=side_effect), \
             patch("sys.argv", ["define", "--shell", "fr"]):
            main()
            mock_wikt.assert_not_called()

    def test_shell_exception_in_fetch_does_not_crash_loop(self):
        inputs = iter(["bonjour", EOFError()])
        def side_effect(prompt=""):
            val = next(inputs)
            if isinstance(val, BaseException):
                raise val
            return val
        with patch("define_cli.main.wiktionary.fetch", side_effect=Exception("network error")), \
             patch("builtins.input", side_effect=side_effect), \
             patch("sys.argv", ["define", "--shell", "fr"]):
            main()  # should not raise
