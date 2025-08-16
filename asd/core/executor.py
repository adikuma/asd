from rich.prompt import Confirm

from ..ui.display import (
    console,
    display_recovery_comparison,
)
from ..ui.loader import stop_loader
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


# lowercase comments as requested
def execute_plan(state: State) -> State:
    stop_loader()
    state.step_results = []
    state.lessons_learned = []
    all_success = True

    for step_index, step in enumerate(state.plan.steps):
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
            console.print(f"[failure]x step blocked: {error_msg}[/failure]")

            if not Confirm.ask("[prompt]> continue?[/prompt]", console=console):
                all_success = False
                break
            continue

        if final_command.startswith("git commit") and "-m" not in final_command:
            diff = get_git_diff_analysis()
            if not diff:
                console.print("[warning]> nothing staged[/warning]")
                continue

            commit_msg, explanation = generate_commit_message(diff)
            final_command = f'git commit -m "{commit_msg}"'
            console.print(f"[info]> generated: {commit_msg}[/info]")

        console.print(f"[info]> executing: {final_command}[/info]")
        result = run_git_command(final_command)

        educational_note = step.educational_note
        safety_note = ""

        if result["success"]:
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
            console.print(f"[failure]x failed: {result['stderr']}[/failure]")
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

        if not result["success"]:
            console.print("[loading] analyzing failure...[/loading]")
            fresh_git_status = get_git_status()
            completed_successful_steps = [r for r in state.step_results if r.success]
            recovery_plan = generate_recovery_plan(
                state, step_result, fresh_git_status, completed_successful_steps
            )

            display_recovery_comparison(state.plan, recovery_plan, step_result.error)
            if Confirm.ask("[prompt] proceed with recovery?[/prompt]", console=console):
                console.print("[info]switching to recovery...[/info]\n")
                state.plan = recovery_plan
                state.recovery_needed = True
                state.lessons_learned.append(
                    f"learned to recover from: {step_result.error}"
                )
                return execute_plan(state)
            else:
                console.print("[warning]stopped by user[/warning]")
                all_success = False
                break

    state.operation_complete = True
    state.operation_success = all_success
    state.final_message = (
        "execution completed successfully"
        if all_success
        else "execution completed with some failures"
    )
    return state
