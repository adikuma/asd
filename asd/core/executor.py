from rich.prompt import Confirm

from ..ui.display import (
    console,
    display_recovery_comparison,
)
from ..ui.prompts import confirm_step_execution
from .git_tools import (
    check_git_prerequisites,
    generate_commit_message,
    get_git_diff_analysis,
    get_git_status,
    run_git_command,
)
from .models import State, StepResult
from .planner import generate_recovery_plan


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

        # if command failed, trigger replanning instead of asking to continue
        if not result["success"]:
            console.print(
                "[loading] analyzing failure and replanning workflow...[/loading]"
            )
            # get fresh git status after failure
            fresh_git_status = get_git_status()
            # create  the recovery context
            completed_successful_steps = [r for r in state.step_results if r.success]
            recovery_plan = generate_recovery_plan(
                state, step_result, fresh_git_status, completed_successful_steps
            )

            # display plan comparison
            display_recovery_comparison(state.plan, recovery_plan, step_result.error)
            # ask user if they want to proceed with recovery plan
            if Confirm.ask(
                "[prompt] proceed with recovery plan?[/prompt]", console=console
            ):
                # update state with recovery plan and restart execution
                console.print("[info]📋 switching to recovery plan...[/info]\n")
                state.plan = recovery_plan
                state.recovery_needed = True
                state.lessons_learned.append(
                    f"learned to recover from: {step_result.error}"
                )

                # recursive call to execute the recovery plan
                return execute_plan(state)
            else:
                console.print("[warning]⏹ execution stopped by user[/warning]")
                all_success = False
                break

    state.operation_complete = True
    state.operation_success = all_success

    if all_success:
        state.final_message = "execution completed successfully"
    else:
        state.final_message = "execution completed with some failures"

    return state
