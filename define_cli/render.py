"""Render lookup results using Rich."""
from __future__ import annotations
from rich.console import Console
from rich.text import Text
from rich.rule import Rule

console = Console()

POS_COLOURS = {
    "Noun":              "cyan",
    "Verb":              "green",
    "Adjective":         "yellow",
    "Adverb":            "magenta",
    "Preposition":       "blue",
    "Interjection":      "red",
    "Conjunction":       "blue",
    "Pronoun":           "cyan",
    "Article":           "dim",
    "Determiner":        "dim",
    "Numeral":           "cyan",
    "Particle":          "dim",
    "Suffix":            "dim",
    "Prefix":            "dim",
    "Proper noun":       "cyan",
    "Phrase":            "white",
    "Idiom":             "white",
    "Proverb":           "dim",
    "Abbreviation":      "dim",
    "Contraction":       "dim",
}


def render(
    word: str,
    lang: str,
    wikt_result: dict,
    reverso_result: dict,
    examples_only: bool = False,
) -> None:
    wikt_status = wikt_result.get("status", "skipped")
    reverso_status = reverso_result.get("status", "skipped")

    wikt_ok = wikt_status == "ok"
    reverso_ok = reverso_status == "ok"
    wikt_skipped = wikt_status == "skipped"
    reverso_skipped = reverso_status == "skipped"

    examples = reverso_result.get("examples") if reverso_ok else None

    if examples_only:
        _render_examples(word, examples)
        return

    # ── Header ──────────────────────────────────────────────────────────────
    header = Text()
    header.append(word, style="bold white")
    if wikt_ok and wikt_result.get("ipa"):
        header.append("  " + wikt_result["ipa"][0], style="dim")
    console.print()
    console.print(header)

    if wikt_ok:
        actual = wikt_result.get("actual_word")
        if actual and actual != word:
            console.print(
                f"  [dim]No results for '{word}', showing results"
                f" for '{actual}'[/dim]"
            )

    # ── Definitions ─────────────────────────────────────────────────────────
    if wikt_ok and wikt_result.get("entries"):
        for entry in wikt_result["entries"]:
            pos = entry["pos"]
            colour = POS_COLOURS.get(pos, "white")
            console.print(f"\n  [{colour}]{pos.lower()}[/{colour}]")
            for i, defn in enumerate(entry["definitions"], 1):
                console.print(f"  [dim]{i}.[/dim] {defn}")
    elif not wikt_skipped:
        if wikt_status == "network_error":
            console.print("  [dim]Could not reach Wiktionary.[/dim]")
        elif wikt_status == "not_found" or wikt_ok:
            console.print("  [dim]No definitions found.[/dim]")

    # ── Examples ────────────────────────────────────────────────────────────
    if examples:
        console.print()
        console.print(Rule(style="dim"))
        for ex in examples:
            console.print(f"  [italic]{ex['source']}[/italic]")
            console.print(f"  [dim]{ex['translation']}[/dim]")
            console.print()
    elif not reverso_skipped:
        if reverso_status == "network_error":
            console.print("\n  [dim]Could not reach examples source.[/dim]\n")
        elif reverso_status in ("not_found", "unsupported"):
            console.print("\n  [dim]No examples found.[/dim]\n")

    # ── Reinstall hint — only when both sources failed non-trivially ─────────
    both_failed = (
        not wikt_skipped and not reverso_skipped
        and wikt_status in ("not_found", "network_error")
        and reverso_status in ("not_found", "network_error", "unsupported")
        and not wikt_ok
    )
    if both_failed:
        console.print(
            "\n  [dim]No results found. If this seems wrong, try:"
            " pipx reinstall define-cli[/dim]\n"
        )


def _render_examples(word: str, examples: list[dict] | None) -> None:
    console.print()
    console.print(Text(f"Examples: {word}", style="bold white"))
    console.print(Rule(style="dim"))
    if not examples:
        console.print("  [dim]No examples found.[/dim]")
        return
    for ex in examples:
        console.print(f"\n  [italic]{ex['source']}[/italic]")
        console.print(f"  [dim]{ex['translation']}[/dim]")
    console.print()
