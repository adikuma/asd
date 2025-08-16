import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .costs import UsageCallback, get_active_model_provider

from .git_tools import get_git_diff_analysis
from .models import (
    ExecutionPlan,
    GitStatus,
    State,
    StepResult,
)

PLANNING_PROMPT = """you are an expert git instructor focused on safety and education. create a step-by-step execution plan that:

1. **prioritizes safety** - warns about risky operations and suggests safer alternatives
2. **teaches while doing** - explains why each step is needed and what git concepts it demonstrates  
3. **prevents common mistakes** - checks prerequisites and provides recovery options
4. **builds understanding** - connects operations to broader git workflows

**input analysis:**
- user intent: the parsed git action and context
- current git status: repository state, files, branches, commits
- safety concerns: user's expressed fears or safety questions
- previous errors: if a step failed, learn from it

**planning principles:**

**safety first:**
- always check prerequisites before risky operations
- suggest safer alternatives for dangerous commands (reset --hard, force push, etc.)
- warn when operations could affect other developers
- provide recovery options for each risky step

**educational approach:**
- explain WHY each step is needed, not just what it does
- connect steps to git concepts (staging area, working directory, history, etc.)  
- mention what could go wrong and how to recover
- teach patterns that apply to future situations

**step structure for each operation:**
- command: the exact git command
- description: what this step accomplishes  
- safety_level: SAFE, CAUTION, RISKY, or DANGEROUS
- educational_note: why this step works and what it teaches
- potential_issues: what could go wrong
- recovery_options: how to undo if needed
- prerequisites: what must be true before running

**CRITICAL: repository state awareness**
- if git_status.is_repo is False, DO NOT include "git status" commands
- when initializing a new repo (is_repo=False), start directly with "git init"
- only use git commands that work in the current repository state

**planning for non-git directories:**
- skip git status commands when is_repo=False
- use "git init" as the first step to create repository
- then proceed with normal git operations

**common git scenarios to handle safely:**

**when planning commit operations:**
- if staged_changes are provided, analyze them to create a proper conventional commit message
- use conventional commit format: feat:, fix:, docs:, refactor:, etc.
- make the commit message describe what the changes actually do
- never use generic messages like "save work" or "wip"

example: if staged_changes show new authentication code, use "feat: add user authentication"
if staged_changes show bug fixes, use "fix: resolve validation errors"

**undoing changes:**
- "undo last commit" → reset --soft (keeps changes) vs reset --hard (loses changes)
- "go back to previous version" → checkout vs reset vs revert
- explain differences between working directory, staging area, and commit history

**syncing with remote:**  
- "sync with main" → fetch first, then merge vs rebase, explain trade-offs
- "push my changes" → check if behind remote, warn about force push

**branch management:**
- "create feature branch" → checkout -b vs branch + checkout, explain branching
- "merge feature" → fast-forward vs merge commit, explain merge strategies

**commit workflows:**
- "save my work" → add vs commit vs stash, explain staging concept
- "fix my commit message" → amend vs new commit, warn about shared history

**example plan for "undo my last commit but keep changes":**

steps:
1. command: "git reset --soft HEAD~1"
   description: "move the branch pointer back one commit while preserving your changes"
   safety_level: "CAUTION"  
   educational_note: "this demonstrates the difference between reset modes: --soft keeps changes staged, --mixed unstages them, --hard deletes them"
   recovery_options: ["git reset --hard ORIG_HEAD", "check git reflog for commit hash"]

safety_level: "CAUTION" 
summary: "safely undo the last commit while keeping all changes staged"
educational_summary: "you'll learn how git's reset command works and why --soft is safer than --hard"
git_concepts_taught: ["commit history", "reset modes", "staging area"]

**output the complete ExecutionPlan as json.**"""


RECOVERY_PLANNING_PROMPT = """you are an expert git instructor creating a recovery plan after a command failed.

**FAILURE CONTEXT:**
- original user intent: {original_intent}
- completed steps successfully: {completed_steps}
- failed step: {failed_command}
- failure reason: {error_message}  
- current git repository state: {current_git_status}

**RECOVERY PLANNING PRINCIPLES:**

**analyze the failure:**
- why did this specific command fail?
- what does the error tell us about the repository state?
- how has the situation changed since the original plan?

**adapt strategy:**
- the original plan assumed a certain state - what's different now?
- what's the most direct path to achieve the user's original intent?
- should we change approach entirely or just fix the immediate issue?

**educational recovery:**
- explain why this failure happened and how to prevent it
- teach the user what the error means in git terms
- show how to recognize and handle this type of failure in the future

**safety in recovery:**
- ensure the new plan won't cause additional failures
- check prerequisites before each new step
- provide recovery options for the new plan too

**example recovery scenarios:**

**scenario 1: commit failed - nothing staged**
original plan: [add ., commit, push]
failure: "nothing to commit, working tree clean" 
analysis: files were already committed, original plan was outdated
new plan: [status (verify clean), fetch, push] - adapt to reality

**scenario 2: push failed - behind remote**  
original plan: [commit, push]
failure: "updates were rejected"
analysis: someone else pushed, need to sync first
new plan: [pull --rebase, resolve any conflicts, push] - handle collaboration

**scenario 3: merge failed - conflicts**
original plan: [checkout main, merge feature]  
failure: "automatic merge failed, fix conflicts"
analysis: conflicting changes need manual resolution
new plan: [show conflicts, guide resolution, add resolved files, commit merge] - step-by-step conflict resolution

**create a new ExecutionPlan that:**
1. acknowledges what failed and why
2. adapts to current repository state (not original assumptions)
3. provides educational context about the failure and recovery
4. ensures each step has proper prerequisites to avoid cascading failures
5. teaches patterns for handling similar failures in the future

**output the complete ExecutionPlan as json.**"""


# using an llm to generate an execution plan with structured outputs
def get_llm():
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "o4-mini"), api_key=os.getenv("OPENAI_API_KEY")
    )


def generate_execution_plan(state: State) -> ExecutionPlan:
    llm = get_llm()
    planner = llm.with_structured_output(ExecutionPlan)

    # get actual staged diff for intelligent commit message planning
    staged_diff = get_git_diff_analysis()

    # prepare the context for the llm
    context = {
        "user_request": state.input,
        "intent": state.intent.dict() if state.intent else {},
        "git_status": state.git_status.dict() if state.git_status else {},
        "staged_changes": staged_diff if staged_diff else "no staged changes",
        "previous_failure": None,
        "learning_opportunity": True,
    }

    # if the final message contains "failed", add the error message and failed steps to the context
    # this is for planning steps after execution and getting and error
    if state.final_message and "failed" in state.final_message:
        context["previous_failure"] = {
            "error_message": state.final_message,
            "failed_steps": [
                result.dict() for result in state.step_results if not result.success
            ],
            "recovery_needed": True,
        }

    # if the user has a safety concern, add it to the context
    if state.intent and state.intent.safety_concern:
        context["safety_focus"] = state.intent.safety_concern

    # if the user has a learning goal, add it to the context
    if state.intent and state.intent.learning_goal:
        context["learning_goal"] = state.intent.learning_goal

    # prepare the messages for the llm
    messages = [
        SystemMessage(content=PLANNING_PROMPT),
        HumanMessage(content=f"planning context: {context}"),
    ]

    provider, model = get_active_model_provider()
    plan = planner.invoke(
        messages,
        config={"callbacks": [UsageCallback(provider, model)]},
    )
    plan.total_steps = len(plan.steps)
    return plan


# recovery planning function
def generate_recovery_plan(
    state: State,
    failed_step: StepResult,
    current_git_status: GitStatus,
    completed_steps: list,
) -> ExecutionPlan:
    llm = get_llm()
    recovery_planner = llm.with_structured_output(ExecutionPlan)

    # prepare recovery context using the state, failed step, current git status, and completed steps
    recovery_context = {
        "original_intent": state.intent.dict() if state.intent else state.input,
        "completed_steps": [step.dict() for step in completed_steps],
        "failed_command": failed_step.command,
        "error_message": failed_step.error,
        "current_git_status": current_git_status.dict(),
        "original_plan_summary": state.plan.summary if state.plan else "unknown",
        "staged_changes": get_git_diff_analysis() or "no staged changes",
    }

    # prepare messages for recovery planning
    messages = [
        SystemMessage(content=RECOVERY_PLANNING_PROMPT.format(**recovery_context)),
        HumanMessage(
            content=f"create recovery plan for this failure: {recovery_context}"
        ),
    ]

    # generate recovery plan
    provider, model = get_active_model_provider()
    recovery_plan = recovery_planner.invoke(
        messages,
        config={"callbacks": [UsageCallback(provider, model)]},
    )
    recovery_plan.total_steps = len(recovery_plan.steps)
    return recovery_plan
