import os

import typer
from dotenv import load_dotenv
from rich.console import Console

from .core.graph import create_git_assistant
from .core.models import State
from .ui.display import (
    display_nerd_stats,
    display_results,
    show_help,
    welcome_screen,
)
from .ui.loader import start_loader, stop_loader
from .ui.prompts import (
    configure_api_key,
    confirm_exit,
    get_user_input,
    select_model,
)
from .ui.themes import THEME

app = typer.Typer(add_completion=False)
console = Console(theme=THEME)


@app.command()
def run():
    # env
    load_dotenv()

    # setup
    configure_api_key()
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        typer.secho("error: no API key configured.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # ui
    welcome_screen()

    assistant = create_git_assistant()
    thread_id = "git_session"
    nerd_stats_enabled = False

    while True:
        user_input = get_user_input()

        if user_input.lower() in ("q", "quit", "exit"):
            if confirm_exit():
                break
            continue

        if user_input.lower() in ("h", "help"):
            show_help()
            continue

        if user_input.lower() in ("m", "model"):
            select_model()
            continue

        # toggle nerd stats (session totals table)
        if user_input.lower() in ("n", "nerd", "stats", "usage"):
            nerd_stats_enabled = not nerd_stats_enabled
            state = "on" if nerd_stats_enabled else "off"
            console.print(f"[info]nerd stats {state}[/info]\n")
            continue

        if not user_input.strip():
            continue

        start_loader("analyzing git context and planning safe approach")

        state = State(input=user_input)
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = assistant.invoke(state, config)
            final_state = State(**result) if isinstance(result, dict) else result
            stop_loader()

            console.print()
            display_results(final_state)  # prints two trailing newlines by design

            if nerd_stats_enabled:
                display_nerd_stats()

        except KeyboardInterrupt:
            console.print("\n[warning]operation cancelled by user[/warning]\n")
            continue
        except Exception as e:
            console.print(f"\n[failure]error: {str(e)}[/failure]")
            console.print(
                "[info]if this persists, check your openai api key and try again[/info]\n"
            )
            continue
        finally:
            stop_loader()

    typer.secho("bubye!", fg=typer.colors.BLUE)


if __name__ == "__main__":
    run()
