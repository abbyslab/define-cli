"""define — CLI vocabulary lookup for language learners.

Usage:
    define fr bonjour
    define nl ingewikkeld
    define fr bonjour -e
    define fr bonjour --extended
"""

from __future__ import annotations
import argparse
import sys
import concurrent.futures
from .render import console
from . import wiktionary, reverso, render

SUPPORTED_LANGS = {
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

DEFAULT_EXAMPLE_COUNT = 3

LANG_NAMES = wiktionary.LANG_SECTION_NAMES


def _debug(msg: str) -> None:
    print(f"[debug] {msg}", file=sys.stderr)


def shell_mode(lang: str) -> None:
    from rich.console import Console
    console = Console()
    console.print(f"  [dim]Shell mode — {LANG_NAMES.get(lang, lang)}. Ctrl+C to exit.[/dim]\n")
    while True:
        try:
            word = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            break
        if not word:
            continue

        try:
            wikt_result = wiktionary.fetch(word, lang)
        except Exception:
            console.print("  [dim]Error fetching data.[/dim]")
            continue

        render.render(
            word=word,
            lang=lang,
            wikt_result=wikt_result,
            reverso_result={"status": "skipped"},
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="define",
        description="Vocabulary lookup: definitions, IPA, and usage examples.",
        add_help=True,
    )
    p.add_argument(
        "lang",
        metavar="LANG",
        nargs="?",
        help=f"Language code ({', '.join(SUPPORTED_LANGS)})",
    )
    p.add_argument(
        "word",
        metavar="WORD",
        nargs="?",
        help="Word to look up",
    )
    p.add_argument(
        "-e", "--extended",
        action="store_true",
        help="Fetch and display all available Reverso examples",
    )
    p.add_argument(
        "--no-defs",
        action="store_true",
        help="Skip Wiktionary (definitions + IPA)",
    )
    p.add_argument(
        "--no-examples",
        action="store_true",
        help="Skip Reverso (usage examples)",
    )
    p.add_argument(
        "--langs",
        action="store_true",
        help="List all supported languages and their codes",
    )
    p.add_argument(
        "--shell",
        metavar="LANG",
        help="Interactive shell mode for a given language",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Print parse diagnostics to stderr",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.langs:
        for code, name in sorted(SUPPORTED_LANGS.items(), key=lambda x: x[1]):
            console.print(f"  [dim]{code}[/dim]  {name}")
        return

    if args.shell:
        lang = args.shell.lower()
        if lang not in SUPPORTED_LANGS:
            print(f"Unsupported language: {lang}", file=sys.stderr)
            sys.exit(1)
        shell_mode(lang)
        return

    if not args.lang or not args.word:
        parser.print_help()
        sys.exit(1)

    lang = args.lang.lower()
    word = args.word

    if not word.strip():
        parser.print_help()
        sys.exit(1)

    if lang not in SUPPORTED_LANGS:
        print(
            f"Unsupported language '{lang}'. "
            f"Supported: {', '.join(SUPPORTED_LANGS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    examples_limit = None if args.extended else DEFAULT_EXAMPLE_COUNT

    wikt_result: dict = {"status": "skipped"}
    reverso_result: dict = {"status": "skipped"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}

        if not args.no_defs:
            futures["wikt"] = pool.submit(wiktionary.fetch, word, lang)

        if not args.no_examples:
            futures["reverso"] = pool.submit(
                reverso.fetch, word, lang, examples_limit
            )

        for key, fut in futures.items():
            try:
                result = fut.result(timeout=15)
            except Exception as exc:
                print(f"[{key}] error: {exc}", file=sys.stderr)
                result = {"status": "network_error"}

            if key == "wikt":
                wikt_result = result
            elif key == "reverso":
                reverso_result = result

    if args.debug:
        _debug(f"wiktionary status: {wikt_result.get('status')}")
        if wikt_result.get("status") == "ok":
            _debug(f"ipa: {wikt_result.get('ipa')}")
            _debug(f"entries: {len(wikt_result.get('entries', []))} POS blocks")
            for e in wikt_result.get("entries", []):
                _debug(f"  {e['pos']}: {len(e['definitions'])} definitions")
        _debug(f"reverso status: {reverso_result.get('status')}")
        if reverso_result.get("status") == "ok":
            _debug(f"examples: {len(reverso_result.get('examples', []))}")

    render.render(
        word=word,
        lang=lang,
        wikt_result=wikt_result,
        reverso_result=reverso_result,
        examples_only=args.extended,
    )


if __name__ == "__main__":
    main()
