from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich_gradient import Gradient

from ..core.costs import fmt_usd, session_usage_snapshot
from .themes import THEME

console = Console(theme=THEME)

# consistent backgrounds
STATUS_BG = "#0f1419"
PLAN_BG = "#0b1116"
RULE_ERR_BG = "#1a1113"


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style="caption", no_wrap=True)
    t.add_column(style="command", overflow="fold")
    for k, v in rows:
        t.add_row(k, v)
    return t


def section_rule(title: str, *, variant: str = "normal"):
    if variant == "error":
        style = f"failure on {RULE_ERR_BG}"
    else:
        style = f"accent on {STATUS_BG}"
    console.print(Rule(f"[header]{title}[/header]", style=style))


def welcome_screen():
    raw_logo = r"""
  █████╗ ███████╗██████╗ 
  ██╔══██╗██╔════╝██╔══██╗
  ███████║███████╗██║  ██║
  ██╔══██║╚════██║██║  ██║
  ██║  ██║███████║██████╔╝
  ╚═╝  ╚═╝╚══════╝╚═════╝ 
    """
    console.clear()
    logo = raw_logo.strip("\n")
    gradient_logo = Gradient(logo, colors=["#3b5b76", "#8fb4d8"])
    console.print(gradient_logo, justify="left")

    console.print("[caption]Tips for getting started:[/caption]")
    tips = [
        "press [educational]h[/educational] for help",
        "press [educational]m[/educational] to select model",
        "press [educational]q[/educational] to quit",
        "press [educational]n[/educational] to toggle nerd stats",
    ]
    for i, t in enumerate(tips, 1):
        console.print(f"[caption]{i}.[/] {t}")
    console.print()


def display_git_status(status):
    section_rule("status")

    rows = [
        ("branch", status.current_branch or "none"),
        ("staged", str(len(status.staged))),
        ("modified", str(len(status.modified))),
        ("untracked", str(len(status.untracked))),
    ]

    if status.has_remote:
        sync = (f"↑{status.ahead}" if status.ahead > 0 else "") + (
            f"↓{status.behind}" if status.behind > 0 else ""
        )
        rows.append(("remote", f"{status.remote_name} ({sync or 'synced'})"))

    if status.uncommitted_changes > 0:
        rows.append(
            (
                "note",
                f"[warning]{status.uncommitted_changes} uncommitted changes[/warning]",
            )
        )
    if status.conflicts:
        rows.append(("conflicts", "[destructive]detected[/destructive]"))

    console.print(
        Panel(
            _kv_table(rows),
            box=box.MINIMAL,
            border_style="caption",
            style=f"on {STATUS_BG}",
            padding=(0, 1),
        )
    )
    console.print()


def display_execution_plan(plan):
    section_rule("plan")

    lines = [
        f"[{plan.overall_safety.lower()}]safety: {plan.overall_safety.lower()}[/{plan.overall_safety.lower()}]"
    ]
    for i, step in enumerate(plan.steps, 1):
        icon = {"safe": "+", "caution": "!", "risky": "!", "dangerous": "x"}.get(
            step.safety_level.lower(), "+"
        )
        lines.append(f"[accent]{icon} {i}.[/accent] [command]{step.command}[/]")
        lines.append(f"  {step.description}")
        if (
            step.safety_level.lower() in {"risky", "dangerous"}
            and step.potential_issues
        ):
            lines.append(f"  [warning]! {step.potential_issues[0]}[/warning]")

    if plan.warnings:
        w = plan.warnings[0]
        lines.append("[warning]warnings:[/warning]")
        lines.append(f"[warning]! {w.message}[/warning]")
        if w.safer_alternatives:
            lines.append(f"  [info]> {w.safer_alternatives[0]}[/info]")

    lines.append("")

    console.print(
        Panel(
            "\n".join(lines),
            # subtitle=f"[info]{plan.summary}[/info]",
            box=box.MINIMAL,
            border_style="accent",
            style=f"on {PLAN_BG}",
            padding=(0, 1, 1, 1),
        )
    )
    console.print()


def display_recovery_comparison(original_plan, recovery_plan, failure_reason):
    section_rule("recovery", variant="error")
    console.print(f"[failure] failure analysis: {failure_reason}[/failure]\n")
    console.print(f"[warning]original: {original_plan.summary}[/warning]")
    console.print(f"[success]recovery: {recovery_plan.summary}[/success]\n")
    console.print(
        f"[educational] why changed: {recovery_plan.educational_summary}[/educational]\n"
    )
    display_execution_plan(recovery_plan)


def display_results(state):
    variant = "error" if not state.operation_success else "normal"
    section_rule("results", variant=variant)

    if state.operation_success:
        icon, style = "+", "success"
    elif state.recovery_needed:
        icon, style = "!", "warning"
    else:
        icon, style = "x", "failure"

    lines = [f"[{style}]{icon} {state.final_message}[/{style}]", ""]

    for result in state.step_results:
        step_icon = "[success]+[/success]" if result.success else "[failure]x[/failure]"
        lines.append(f"{step_icon} [command]{result.command}[/]")
        if result.success and result.output:
            out = "  " + result.output.replace("\n", "\n  ")
            lines.append(f"  [info]{out}[/info]")
            # empty line
            lines.append("")
        elif not result.success and result.error:
            err = "  " + result.error.replace("\n", "\n  ")
            lines.append(f"  [failure]{err}[/failure]")

    if state.lessons_learned:
        lines.append("")
        lines.append("[accent]learned:[/accent]")
        for lesson in list(set(state.lessons_learned))[:3]:
            lines.append(f"[note]> {lesson}[/note]")
            # empty line
            lines.append("")

    panel_style = f"on {RULE_ERR_BG}" if variant == "error" else f"on {STATUS_BG}"
    console.print(
        Panel(
            "\n".join(lines),
            box=box.MINIMAL,
            border_style="caption",
            style=panel_style,
            padding=(0, 1),
        )
    )
    console.print()
    console.print()


def show_help():
    section_rule("help")

    lines = [
        "[accent]h[/accent]  [info]help[/info]",
        "[accent]m[/accent]  [info]select model[/info]",
        "[accent]n[/accent]  [info]nerd stats (toggle)[/info]",
        "[accent]q[/accent]  [info]quit[/info]",
        "",
        "[header]example git tasks:[/header]",
        "[info]undo my last commit but keep changes[/info]",
        "[info]safely merge main into my branch[/info]",
        "[info]clean up my commit history[/info]",
        "[info]help me resolve merge conflicts[/info]",
        "[info]push my changes without breaking things[/info]",
        "[info]what would happen if i reset --hard?[/info]",
        "",
        "[caption]asd focuses on git safety and education[/caption]",
    ]

    console.print(
        Panel(
            "\n".join(lines),
            box=box.MINIMAL,
            border_style="caption",
            style=f"on {STATUS_BG}",
            padding=(1, 1),
        )
    )
    console.print()


def display_nerd_stats():
    snap = session_usage_snapshot()
    grand = snap.get("grand", {})
    models = snap.get("models", [])

    section_rule("nerd stats")

    if not grand or int(grand.get("calls", 0)) == 0:
        console.print("[caption]no llm usage yet[/caption]\n")
        return

    # clean minimal table
    tbl = Table(show_header=False, box=None, padding=(0, 2))
    tbl.add_column(style="command")
    tbl.add_column(justify="right", style="info")
    tbl.add_column(justify="right", style="accent")

    # add model rows
    for r in sorted(models, key=lambda x: float(x.get("cost", 0.0)), reverse=True):
        model = f"{r.get('provider', '-')}:{r.get('model', '-')}"
        tokens = (
            f"{int(r.get('prompt_tokens', 0)) + int(r.get('completion_tokens', 0)):,}"
        )
        cost = fmt_usd(float(r.get("cost", 0.0)))
        tbl.add_row(model, tokens, cost)

    # add total if multiple models
    if len(models) > 1:
        tbl.add_row("", "", "")  # spacer
        total_tokens = int(grand.get("prompt_tokens", 0)) + int(
            grand.get("completion_tokens", 0)
        )
        total_cost = fmt_usd(float(grand.get("cost", 0.0)))
        total_calls = int(grand.get("calls", 0))
        tbl.add_row(
            f"[caption]total ({total_calls:,})[/caption]",
            f"[caption]{total_tokens:,}[/caption]",
            f"[accent]{total_cost}[/accent]",
        )

    console.print(tbl)
    console.print()
