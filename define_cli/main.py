"""define — CLI vocabulary lookup for language learners.

Usage:
    define fr bonjour
    define nl ingewikkeld
    define fr bonjour -e
    define fr bonjour --examples
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

DEFAULT_EXAMPLE_COUNT = 5


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
        "-e", "--examples",
        action="store_true",
        help="Fetch and display all available Reverso examples",
    )
    p.add_argument(
        "--no-wikt",
        action="store_true",
        help="Skip Wiktionary (definitions + IPA)",
    )
    p.add_argument(
        "--no-reverso",
        action="store_true",
        help="Skip Reverso (usage examples)",
    )
    p.add_argument(
        "--langs",
        action="store_true",
        help="List all supported languages and their codes",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.langs:
        for code, name in sorted(SUPPORTED_LANGS.items(), key=lambda x: x[1]):
            console.print(f"  [dim]{code}[/dim]  {name}")
        return

    lang = args.lang.lower()
    word = args.word

    if lang not in SUPPORTED_LANGS:
        print(
            f"Unsupported language '{lang}'. "
            f"Supported: {', '.join(SUPPORTED_LANGS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.lang or not args.word:
        parser.print_help()
        sys.exit(1)

    examples_limit = None if args.examples else DEFAULT_EXAMPLE_COUNT

    # Fetch sources concurrently
    wikt_data = None
    reverso_data = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}

        if not args.no_wikt:
            futures["wikt"] = pool.submit(wiktionary.fetch, word, lang)

        if not args.no_reverso:
            futures["reverso"] = pool.submit(
                reverso.fetch, word, lang, examples_limit
            )

        for key, fut in futures.items():
            try:
                result = fut.result(timeout=15)
            except Exception as exc:
                print(f"[{key}] error: {exc}", file=sys.stderr)
                result = None

            if key == "wikt":
                wikt_data = result
            elif key == "reverso":
                reverso_data = result

    render.render(
        word=word,
        lang=lang,
        wikt_data=wikt_data,
        reverso_data=reverso_data,
        examples_only=args.examples,
    )


if __name__ == "__main__":
    main()
