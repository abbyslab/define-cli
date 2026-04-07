"""Render lookup results using Rich."""

from __future__ import annotations
from rich.console import Console
from rich.text import Text
from rich.rule import Rule
from rich import print as rprint

console = Console()

POS_COLOURS = {
    "Noun":        "cyan",
    "Verb":        "green",
    "Adjective":   "yellow",
    "Adverb":      "magenta",
    "Preposition": "blue",
    "Interjection":"red",
    "Conjunction": "blue",
    "Pronoun":     "cyan",
    "Article":     "dim",
    "Determiner":  "dim",
    "Numeral":     "cyan",
    "Particle":    "dim",
    "Suffix":      "dim",
    "Prefix":      "dim",
}


def render(
    word: str,
    lang: str,
    wikt_data: dict | None,
    reverso_data: list[dict] | None,
    examples_only: bool = False,
) -> None:

    if examples_only:
        _render_examples(word, reverso_data)
        return

    # ── Header ──────────────────────────────────────────────────────────────
    header = Text()
    header.append(word, style="bold white")

    if wikt_data and wikt_data.get("ipa"):
        ipa_str = "  " + wikt_data["ipa"][0]
        header.append(ipa_str, style="dim")

    console.print()
    console.print(header)

    # ── Definitions ─────────────────────────────────────────────────────────
    if wikt_data and wikt_data.get("entries"):
        for entry in wikt_data["entries"]:
            pos = entry["pos"]
            colour = POS_COLOURS.get(pos, "white")
            console.print(f"\n  [{colour}]{pos.lower()}[/{colour}]")
            for i, defn in enumerate(entry["definitions"], 1):
                console.print(f"  [dim]{i}.[/dim] {defn}")
    elif not examples_only:
        console.print("  [dim]No definitions found.[/dim]")

    # ── Examples (short) ────────────────────────────────────────────────────
    if reverso_data:
        console.print()
        console.print(Rule(style="dim"))
        for ex in reverso_data:
            console.print(f"  [italic]{ex['source']}[/italic]")
            console.print(f"  [dim]{ex['translation']}[/dim]")
            console.print()

    # Hint if everything came back empty
    no_defs = not wikt_data or (not wikt_data.get("ipa") and not wikt_data.get("entries"))
    no_examples = not reverso_data
    if no_defs and no_examples:
        console.print(
            "\n  [dim]No results found. If this seems wrong, try:"
            " pipx reinstall define-cli[/dim]\n"
        )
    elif no_examples:
        console.print("\n  [dim]No examples found.[/dim]\n")

def _render_examples(word: str, reverso_data: list[dict] | None) -> None:
    console.print()
    console.print(Text(f"Examples: {word}", style="bold white"))
    console.print(Rule(style="dim"))

    if not reverso_data:
        console.print("  [dim]No examples found.[/dim]")
        return

    for ex in reverso_data:
        console.print(f"\n  [italic]{ex['source']}[/italic]")
        console.print(f"  [dim]{ex['translation']}[/dim]")

    console.print()
