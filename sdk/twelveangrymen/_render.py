"""
Rendering for Verdict.summary(). Uses `rich` for nicely formatted, color-coded
output when available, since it's a lightweight, pure-Python dependency with
no compiled extensions. Falls back to plain text if rich isn't installed, so
summary() never hard-fails just because of a missing optional dependency.
"""

_SCORE_LABELS = {0: "clear", 1: "possible violation", 2: "violation"}


def _cake_art(color: str) -> str:
    # A small sentiment cue: a cherry on top for a fully clear verdict, a
    # caution mark for "possible," a cross for a clear violation.
    topper = {"green": "\U0001F352", "yellow": "!", "red": "X"}[color]
    return (
        f"      {topper}\n"
        "   .-'''''-.\n"
        "  /  JURY   \\\n"
        "  '._______.'\n"
    )


def render_verdict_summary(verdict) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        _render_plain(verdict)
        return

    color = verdict.color
    art = Text(_cake_art(color), style=f"bold {color}", justify="center")

    table = Table(show_header=True, header_style=f"bold {color}", expand=True)
    table.add_column("Rule")
    table.add_column("Verdict", justify="center")
    for rule_name, score in verdict.scores.items():
        style = {0: "dim", 1: "yellow", 2: "bold red"}[score]
        table.add_row(rule_name, Text(_SCORE_LABELS[score], style=style))

    body = Table.grid(padding=(0, 0))
    body.add_row(art)
    body.add_row(table)
    body.add_row(Text(""))
    body.add_row(Text(verdict.details, style="italic"))

    title = verdict.policy_name or "Policy"
    console = Console()
    console.print(
        Panel(
            body,
            title=f"[bold {color}]{title} \u2014 {color.upper()}[/bold {color}]",
            border_style=color,
            expand=False,
        )
    )


def _render_plain(verdict) -> None:
    print(f"=== {verdict.policy_name or 'Policy'} \u2014 verdict: {verdict.color.upper()} ===")
    for rule_name, score in verdict.scores.items():
        print(f"  - {rule_name}: {_SCORE_LABELS[score]} ({score})")
    print(f"\n{verdict.details}\n")