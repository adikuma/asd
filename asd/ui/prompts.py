import os

import questionary
from questionary import Style as QStyle  # custom style for questionary
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .display import display_execution_plan, display_git_status
from .themes import SYMBOLS, THEME

console = Console(theme=THEME)

# unified dropdown style to match the ui palette
# keys are prompt_toolkit style tokens used by questionary
QSTYLE = QStyle(
    [
        ("qmark", "fg:#8fb4d8 bold"),
        ("question", "fg:#8fb4d8 bold"),
        ("answer", "fg:#8fb4d8"),
        ("pointer", "fg:#8fb4d8 bold"),
        ("highlighted", "fg:#0f1419 bg:#8fb4d8"),
        ("selected", "fg:#0f1419 bg:#8fb4d8"),
        ("separator", "fg:#5a6472"),
        ("instruction", "fg:#5a6472"),
        ("text", "fg:#e6edf3"),
        ("disabled", "fg:#5a6472 italic"),
    ]
)


def configure_api_key() -> bool:
    if os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return True

    console.print(
        Panel("[info]no api key found[/info]", title="[header]Setup[/header]", width=40)
    )

    provider = questionary.select(
        "Select provider",
        choices=["OpenAI", "Google"],
        style=QSTYLE,
    ).ask()
    if not provider:
        console.print("[warning]setup cancelled[/warning]")
        return False

    key = questionary.password("Enter API key", style=QSTYLE).ask()
    if not key or not key.strip():
        console.print("[failure]no key entered[/failure]")
        return False

    key = key.strip()
    if provider == "OpenAI":
        os.environ["OPENAI_API_KEY"] = key
        os.environ["PROVIDER"] = "openai"
    else:
        os.environ["GOOGLE_API_KEY"] = key
        os.environ["PROVIDER"] = "google"

    console.print(f"[success]api key saved for {provider.lower()}[/success]")
    return True


def get_user_input() -> str:
    return Prompt.ask(
        f"[input]{SYMBOLS['prompt']} git task or question?[/input]", console=console
    ).strip()


def confirm_exit() -> bool:
    return Confirm.ask(
        f"[prompt]{SYMBOLS['prompt']} quit git assistant?[/prompt]", console=console
    )


def select_model():
    providers = []
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("openai", "OpenAI"))
    if os.getenv("GOOGLE_API_KEY"):
        providers.append(("google", "Google"))

    if not providers:
        console.print(
            "[failure]no provider configured. set an api key first.[/failure]"
        )
        return

    if len(providers) > 1:
        menu = "\n".join(
            f"[accent]{i}.[/] {name}" for i, (k, name) in enumerate(providers, 1)
        )
        console.print(Panel(menu, title="[header]Select Provider[/header]", width=40))
        p = Prompt.ask(
            "Choice",
            choices=[str(i) for i in range(1, len(providers) + 1)],
            console=console,
        )
        provider = providers[int(p) - 1][0]
    else:
        provider = providers[0][0]

    if provider == "openai":
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "o4-mini"]
        current = os.getenv("OPENAI_MODEL", "o4-mini")
    else:
        models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
        current = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

    display_choices = [
        f"{m} {'← current' if m == current else ''}".strip() for m in models
    ]

    selected_display = questionary.select(
        "Select model",
        choices=display_choices,
        default=next(c for c in display_choices if "← current" in c),
        style=QSTYLE,
    ).ask()

    sel = selected_display.split(" ")[0]
    if provider == "openai":
        os.environ["OPENAI_MODEL"] = sel
    else:
        os.environ["GOOGLE_MODEL"] = sel

    console.print(f"» model set to {sel}\n")


def modify_command(current_command: str) -> str:
    console.print(f"[info]current: {current_command}[/info]")
    new_command = Prompt.ask(
        f"[prompt]{SYMBOLS['prompt']} enter new command[/prompt]",
        console=console,
        default=current_command,
    )
    return new_command.strip()


def confirm_step_execution(
    step, step_number: int, total_steps: int
) -> tuple[bool, str]:
    console.print(f"\n[accent]step {step_number}/{total_steps}[/accent]")
    console.print(f"[command]{step.command}[/]")
    console.print(f"[info]{step.description}[/info]")

    if step.safety_level.lower() in ["risky", "dangerous"]:
        console.print(
            f"[{step.safety_level.lower()}]! {step.safety_level.lower()} operation[/{step.safety_level.lower()}]"
        )

    while True:
        choice = Prompt.ask(
            f"[prompt]{SYMBOLS['prompt']} execute this command?[/prompt] [choice][y/n/modify][/choice]",
            choices=["y", "n", "modify"],
            console=console,
            default="y",
            show_choices=True,
            show_default=False,
        ).lower()

        if choice in ["y", "yes"]:
            return True, step.command
        elif choice in ["n", "no"]:
            return False, step.command
        elif choice in ["modify", "m"]:
            new_command = modify_command(step.command)
            console.print(f"[success]+ updated to: {new_command}[/success]")
            return True, new_command


def confirm_plan(state) -> bool:
    console.print()
    display_git_status(state.git_status)
    display_execution_plan(state.plan)
    lvl = state.plan.overall_safety.lower()

    if lvl == "dangerous":
        msg = f"[failure]{SYMBOLS['prompt']} this operation is dangerous! proceed anyway?[/failure]"
    elif lvl == "risky":
        msg = f"[destructive]{SYMBOLS['prompt']} this operation is risky. continue?[/destructive]"
    elif lvl == "caution":
        msg = f"[warning]{SYMBOLS['prompt']} proceed with caution?[/warning]"
    else:
        msg = f"[prompt]{SYMBOLS['prompt']} execute this plan?[/prompt]"

    if lvl in ["dangerous", "risky"] and state.plan.warnings:
        console.print()
        console.print(
            "[warning]> tip: you can type 'n' to see safer alternatives[/warning]"
        )

    return Confirm.ask(msg, console=console)
