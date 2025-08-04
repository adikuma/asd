import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .display import display_execution_plan, display_git_status
from .themes import SYMBOLS, THEME

console = Console(theme=THEME)


# function to configure the api key set in user's environment
def configure_api_key():
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        opts = "[accent]1.[/] OpenAI\n[accent]2.[/] Google AI"
        console.print(Panel(opts, title="[header]No API Key Found[/header]", width=40))
        provider = Prompt.ask("Select provider", choices=["1", "2"], console=console)
        key = Prompt.ask("Enter API key", console=console)  # no password=True
        if provider == "1":
            os.environ["OPENAI_API_KEY"] = key
        else:
            os.environ["GOOGLE_API_KEY"] = key


def get_user_input() -> str:
    # prompt for git task or question
    return Prompt.ask(
        f"[input]{SYMBOLS['prompt']} git task or question?[/input]", console=console
    ).strip()


def confirm_exit() -> bool:
    # prompt to confirm exit
    return Confirm.ask(
        f"[prompt]{SYMBOLS['prompt']} quit git assistant?[/prompt]", console=console
    )


# if user has multiple providers, prompt to select one
# detect the provider set in the environment and select the defaults
def select_model():
    providers = []
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("openai", "OpenAI"))
    if os.getenv("GOOGLE_API_KEY"):
        providers.append(("google", "Google"))
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
        default = os.getenv("OPENAI_MODEL", "o4-mini")
    else:
        models = [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]
        default = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    menu = "\n".join(
        f"[accent]{i}.[/] {m}{' [success]← current[/]' if m == default else ''}"
        for i, m in enumerate(models, 1)
    )
    console.print(
        Panel(menu, title=f"[header]{provider.title()} Models[/header]", width=50)
    )
    c = Prompt.ask(
        "Select model",
        choices=[str(i) for i in range(1, len(models) + 1)],
        console=console,
    )
    sel = models[int(c) - 1]
    if provider == "openai":
        os.environ["OPENAI_MODEL"] = sel
    else:
        os.environ["GOOGLE_MODEL"] = sel
    console.print(f"[success]model set to {sel}[/success]\n")


# function to modify the command
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
            f"[prompt]{SYMBOLS['prompt']} execute this command? [y/n/modify][/prompt]",
            choices=["y", "n", "modify"],
            console=console,
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
    safety_level = state.plan.overall_safety.lower()

    if safety_level == "dangerous":
        prompt_msg = f"[failure]{SYMBOLS['prompt']} this operation is dangerous! proceed anyway?[/failure]"
    elif safety_level == "risky":
        prompt_msg = f"[destructive]{SYMBOLS['prompt']} this operation is risky. continue?[/destructive]"
    elif safety_level == "caution":
        prompt_msg = f"[warning]{SYMBOLS['prompt']} proceed with caution?[/warning]"
    else:
        prompt_msg = f"[prompt]{SYMBOLS['prompt']} execute this plan?[/prompt]"

    if safety_level in ["dangerous", "risky"] and state.plan.warnings:
        console.print()
        console.print(
            "[warning]> tip: you can type 'n' to see safer alternatives[/warning]"
        )

    return Confirm.ask(prompt_msg, console=console)
