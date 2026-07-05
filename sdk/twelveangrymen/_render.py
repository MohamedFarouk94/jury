"""
Rendering for Verdict.summary(). Uses `rich` for nicely formatted, color-coded
output when available, since it's a lightweight, pure-Python dependency with
no compiled extensions. Falls back to plain text if rich isn't installed, so
summary() never hard-fails just because of a missing optional dependency.
"""

_SCORE_LABELS = {0: "clear", 1: "possible violation", 2: "violation"}

# One face per juror, since a Verdict is the panel's collective sentiment.
_FACES = {
    "green": "\U0001F60A",   # 😊 happy
    "yellow": "\U0001F610",  # 😐 neutral
    "red": "\U0001F620",     # 😠 angry
}


def _jury_art(color: str, per_row: int = 4) -> str:
    """A 4x3 grid of the twelve jurors, all wearing the verdict's sentiment."""
    face = _FACES[color]
    rows = []
    for i in range(0, 12, per_row):
        rows.append(" ".join([face] * min(per_row, 12 - i)))
    return "\n".join(rows)


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
    art = Text(_jury_art(color), style=f"bold {color}", justify="center")

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


# State labels/styles for rules shown in a policy summary, including staged
# (not-yet-committed) states -- useful to see at a glance before commit().
_RULE_STATE_LABELS = {
    "persistent": "committed",
    "dirty": "edited (uncommitted)",
    "pending": "new (uncommitted)",
    "pending_delete": "deleted (uncommitted)",
}
_RULE_STATE_STYLES = {
    "persistent": "dim",
    "dirty": "yellow",
    "pending": "green",
    "pending_delete": "red",
}


def render_policy_summary(policy) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        _render_policy_plain(policy)
        return

    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("#", justify="right", width=3)
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Status", justify="center")

    # Committed rules first, in index order; staged-new rules (no index yet) after.
    committed = sorted(
        (r for r in policy.rules.values() if r.policy_rule_index is not None),
        key=lambda r: r.policy_rule_index,
    )
    staged_new = [r for r in policy.rules.values() if r.policy_rule_index is None]

    for rule in committed + staged_new:
        state = rule._state.value
        index_display = str(rule.policy_rule_index) if rule.policy_rule_index is not None else "\u2013"
        table.add_row(
            index_display,
            rule.name,
            rule.description,
            Text(_RULE_STATE_LABELS.get(state, state), style=_RULE_STATE_STYLES.get(state, "")),
        )

    if not policy.rules:
        table.add_row("\u2013", "[dim]no rules yet[/dim]", "", "")

    body = Table.grid(padding=(0, 0))
    if policy.description:
        body.add_row(Text(policy.description, style="italic"))
        body.add_row(Text(""))
    body.add_row(table)

    console = Console()
    console.print(
        Panel(
            body,
            title=f"[bold]{policy.name}[/bold]",
            subtitle=f"{len(committed)} committed rule(s)"
            + (f", {len(staged_new)} staged" if staged_new else ""),
            expand=False,
        )
    )


def _render_policy_plain(policy) -> None:
    print(f"=== {policy.name} ===")
    if policy.description:
        print(policy.description)
    if not policy.rules:
        print("  (no rules yet)")
        return
    committed = sorted(
        (r for r in policy.rules.values() if r.policy_rule_index is not None),
        key=lambda r: r.policy_rule_index,
    )
    staged_new = [r for r in policy.rules.values() if r.policy_rule_index is None]
    for rule in committed + staged_new:
        index_display = rule.policy_rule_index if rule.policy_rule_index is not None else "-"
        state = _RULE_STATE_LABELS.get(rule._state.value, rule._state.value)
        print(f"  [{index_display}] {rule.name}: {rule.description}  ({state})")