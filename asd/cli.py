import os

import typer
from dotenv import load_dotenv
from rich.console import Console

from .core.graph import create_git_assistant
from .core.models import State
from .ui.display import display_results, show_help, welcome_screen
from .ui.prompts import (
    THEME,
    configure_api_key,
    confirm_exit,
    get_user_input,
    select_model,
)

app = typer.Typer(add_completion=False)
console = Console(theme=THEME)


@app.command()
def run():
    # load environment variables
    load_dotenv()

    configure_api_key()
    # check for required api key
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        typer.secho("error: no API key configured.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # show welcome screen
    welcome_screen()

    # create git assistant with enhanced safety and education
    assistant = create_git_assistant()
    thread_id = "git_session"

    # main interaction loop
    while True:
        user_input = get_user_input()

        # handle special commands
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

        # skip empty input
        if not user_input.strip():
            continue

        # show thinking indicator
        console.print(
            "[loading]analyzing git context and planning safe approach[/loading]"
        )

        state = State(input=user_input)
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = assistant.invoke(state, config)
            final_state = State(**result) if isinstance(result, dict) else result

            console.print()
            display_results(final_state)

        except KeyboardInterrupt:
            console.print("\n[warning]operation cancelled by user[/warning]")
            continue
        except Exception as e:
            console.print(f"\n[failure]error: {str(e)}[/failure]")
            console.print(
                "[info]if this persists, check your openai api key and try again[/info]"
            )
            continue

    typer.secho("bubye!", fg=typer.colors.BLUE)


if __name__ == "__main__":
    run()
