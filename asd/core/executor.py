from rich.prompt import Confirm

from ..ui.display import console
from ..ui.prompts import confirm_step_execution
from .git_tools import (
    check_git_prerequisites,
    generate_commit_message,
    get_git_diff_analysis,
    run_git_command,
)
from .models import State, StepResult


def execute_plan(state: State) -> State:
    state.step_results = []
    state.lessons_learned = []
    all_success = True

    console.print(
        f"\n[accent]executing {len(state.plan.steps)} steps with approval[/accent]"
    )

    for step_index, step in enumerate(state.plan.steps):
        # get user approval for this specific step
        should_execute, final_command = confirm_step_execution(
            step, step_index + 1, len(state.plan.steps)
        )

        if not should_execute:
            console.print("[warning]> step skipped[/warning]")
            result = StepResult(
                command=final_command,
                success=True,
                output="step skipped by user",
                error="",
                educational_note="skipping steps gives you control over the process",
                safety_note="you chose to skip this operation",
            )
            state.step_results.append(result)
            continue

        # update command if it was modified
        step.command = final_command

        safety_issues = check_git_prerequisites(final_command, state.git_status)
        if safety_issues:
            error_msg = f"prerequisite check failed: {'; '.join(safety_issues)}"
            result = StepResult(
                command=final_command,
                success=False,
                output="",
                error=error_msg,
                educational_note="this teaches us to always check git status before running commands",
                safety_note="checking prerequisites prevents common git mistakes",
            )
            state.step_results.append(result)
            console.print(f"[failure]x step blocked for safety: {error_msg}[/failure]")

            # ask if user wants to continue with remaining steps
            if not Confirm.ask(
                "[prompt]> continue with remaining steps?[/prompt]", console=console
            ):
                all_success = False
                break
            continue

        if final_command.startswith("git commit") and "-m" not in final_command:
            diff = get_git_diff_analysis()
            if not diff:
                console.print("[warning]> nothing staged to commit[/warning]")
                continue

            commit_msg, explanation = generate_commit_message(diff)
            final_command = f'git commit -m "{commit_msg}"'
            console.print(f"[info]> generated commit message: {commit_msg}[/info]")

        # show execution progress
        console.print(f"[info]> executing: {final_command}[/info]")
        result = run_git_command(final_command)

        educational_note = step.educational_note
        safety_note = ""

        if result["success"]:
            console.print("[success]+ command completed[/success]")
            if result["stdout"]:
                output = (
                    result["stdout"][:100] + "..."
                    if len(result["stdout"]) > 100
                    else result["stdout"]
                )
                console.print(f"[info]  {output}[/info]")

            # TODO: could be made more robust and automated with an LLM
            if "commit" in final_command:
                educational_note += " this creates a permanent snapshot in git history"
                state.lessons_learned.append(
                    "commits create permanent snapshots of your staged changes"
                )
            elif "push" in final_command:
                educational_note += (
                    " this shares your commits with the remote repository"
                )
                state.lessons_learned.append(
                    "pushing makes your commits available to collaborators"
                )
        else:
            console.print(f"[failure]x command failed: {result['stderr']}[/failure]")
            all_success = False

        step_result = StepResult(
            command=final_command,
            success=result["success"],
            output=result["stdout"],
            error=result["stderr"],
            educational_note=educational_note,
            safety_note=safety_note,
        )

        state.step_results.append(step_result)

        # if command failed, ask if user wants to continue
        if not result["success"]:
            if not Confirm.ask(
                "[prompt]> continue with remaining steps?[/prompt]", console=console
            ):
                break

    state.operation_complete = True
    state.operation_success = all_success

    if all_success:
        state.final_message = "execution completed successfully"
    else:
        state.final_message = "execution completed with some failures"

    return state


# manually checking for recoverable errors
# TODO: could be made more robust and automated with an LLM
def _is_recoverable_error(error_msg: str, command: str) -> bool:
    recoverable_patterns = [
        "nothing to commit",
        "already up to date",
        "no changes added to commit",
        "pathspec .* did not match any files",
    ]

    return any(pattern in error_msg.lower() for pattern in recoverable_patterns)


# manually getting the recovery message
# TODO: could be made more robust and automated with an LLM
def _get_recovery_message(error_msg: str, command: str, step) -> str:
    error_lower = error_msg.lower()

    if "nothing to commit" in error_lower:
        return (
            "no changes to commit. this is normal if you've already committed everything. "
            "use 'git status' to see what's happening."
        )

    if "already up to date" in error_lower:
        return (
            "your branch is already current with the remote. this means the operation "
            "was unnecessary but harmless."
        )

    if "no changes added to commit" in error_lower:
        return (
            "you need to stage files first with 'git add <file>' before committing. "
            "this is git's two-step commit process: stage, then commit."
        )

    if "pathspec" in error_lower and "did not match" in error_lower:
        return (
            "the file or path specified doesn't exist. check your spelling and "
            "use 'git status' to see available files."
        )

    if step.recovery_options:
        return (
            f"operation failed. suggested recovery: {'; '.join(step.recovery_options)}"
        )

    return f"operation failed: {error_msg}"
