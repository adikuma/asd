from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# added all git actions
class GitAction(str, Enum):
    ADD = "add"
    COMMIT = "commit"
    PUSH = "push"
    PULL = "pull"
    FETCH = "fetch"
    MERGE = "merge"
    REBASE = "rebase"
    RESET = "reset"
    CHECKOUT = "checkout"
    BRANCH = "branch"
    STATUS = "status"

    STASH = "stash"
    TAG = "tag"
    CHERRY_PICK = "cherry_pick"
    REVERT = "revert"
    SQUASH = "squash"
    AMEND = "amend"
    REMOTE_ADD = "remote_add"
    REMOTE_REMOVE = "remote_remove"

    CLEAN = "clean"
    PRUNE = "prune"
    REFLOG = "reflog"
    LOG = "log"
    DIFF = "diff"
    SHOW = "show"


class SafetyLevel(str, Enum):
    SAFE = "safe"  # operations that are easily reversible
    CAUTION = "caution"  # operations that modify history but are recoverable
    RISKY = "risky"  # operations that could lose work or affect others
    DANGEROUS = "dangerous"  # operations that could cause data loss


# the intent is a model to store the user's intent
class Intent(BaseModel):
    primary_action: GitAction = Field(..., description="main git action to perform")
    secondary_actions: List[GitAction] = Field(
        default_factory=list, description="follow-up git actions in order"
    )
    safety_concern: Optional[str] = Field(
        None, description="user's expressed safety concerns or fears"
    )
    learning_goal: Optional[str] = Field(
        None, description="what the user wants to understand about git"
    )
    targets: Optional[List[str]] = Field(
        None, description="files, branches, or commits to operate on"
    )
    remote_url: Optional[str] = Field(
        None, description="repository url for remote operations"
    )
    branch_name: Optional[str] = Field(None, description="target branch for operations")
    commit_message: Optional[str] = Field(
        None, description="commit message if provided by user"
    )
    force_requested: bool = Field(
        False, description="user explicitly requested force operation"
    )


# a model to store the entire git status of the repo (to give better context to the LLM)
class GitStatus(BaseModel):
    is_repo: bool = Field(False, description="inside a git repository")
    current_branch: str = Field("", description="active branch name")
    staged: List[str] = Field(default_factory=list, description="staged files")
    modified: List[str] = Field(default_factory=list, description="modified files")
    untracked: List[str] = Field(default_factory=list, description="untracked files")
    ahead: int = Field(0, description="commits ahead of origin")
    behind: int = Field(0, description="commits behind origin")
    conflicts: bool = Field(False, description="merge conflicts present")

    # enhanced git context
    total_commits: int = Field(0, description="total commits in current branch")
    uncommitted_changes: int = Field(0, description="number of modified + staged files")
    has_remote: bool = Field(False, description="repository has remote configured")
    remote_name: str = Field("", description="primary remote name")
    last_commit_hash: str = Field("", description="hash of most recent commit")
    last_commit_message: str = Field("", description="message of most recent commit")
    stash_count: int = Field(0, description="number of stashed changes")


# the execution step is a single step in the execution plan
class ExecutionStep(BaseModel):
    command: str = Field(..., description="git command to execute")
    description: str = Field(..., description="what this step does")
    safety_level: SafetyLevel = Field(
        ..., description="safety assessment of this operation"
    )
    educational_note: str = Field(
        ..., description="why this step is needed and what it teaches"
    )
    potential_issues: List[str] = Field(
        default_factory=list, description="things that could go wrong"
    )
    recovery_options: List[str] = Field(
        default_factory=list, description="how to undo if something goes wrong"
    )
    prerequisites: List[str] = Field(
        default_factory=list, description="what should be true before running this"
    )


# the safety warning is a list of warnings that are displayed to the user
class SafetyWarning(BaseModel):
    level: SafetyLevel = Field(..., description="severity of the warning")
    message: str = Field(..., description="explanation of the risk")
    safer_alternatives: List[str] = Field(
        default_factory=list, description="alternative approaches that are safer"
    )
    can_proceed: bool = Field(True, description="whether operation can safely proceed")


# the execution plan is a list of steps to execute
class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep] = Field(..., description="ordered steps to execute")
    total_steps: int = Field(..., description="number of steps in plan")
    overall_safety: SafetyLevel = Field(..., description="safety level of entire plan")
    summary: str = Field(..., description="high-level explanation of what will happen")
    educational_summary: str = Field(
        ..., description="what the user will learn from this"
    )
    warnings: List[SafetyWarning] = Field(
        default_factory=list, description="safety warnings and alternatives"
    )
    git_concepts_taught: List[str] = Field(
        default_factory=list, description="git concepts this plan demonstrates"
    )


# the result of each step in the execution plan
class StepResult(BaseModel):
    command: str = Field(..., description="command that was executed")
    success: bool = Field(..., description="whether command succeeded")
    output: str = Field("", description="stdout from command")
    error: str = Field("", description="stderr from command")
    educational_note: str = Field("", description="what this result teaches")
    safety_note: str = Field("", description="safety implications of this result")


# recovery plan model
class RecoveryContext(BaseModel):
    original_intent: Intent = Field(..., description="user's original request")
    completed_steps: List[StepResult] = Field(
        default_factory=list, description="steps that completed successfully"
    )
    failed_step: StepResult = Field(..., description="the step that failed")
    current_git_status: GitStatus = Field(
        ..., description="fresh git status after failure"
    )
    failure_type: str = Field(
        ..., description="category of failure for recovery strategy"
    )
    original_plan_summary: str = Field(
        ..., description="what the original plan was trying to do"
    )


# the state of the graph
class State(BaseModel):
    # the user's input
    input: str = Field(..., description="user's natural language request")
    # the user's intent is stored in the intent model
    intent: Optional[Intent] = None
    # the git status is stored in the git status model
    git_status: Optional[GitStatus] = None
    # the execution plan is stored in the execution plan model
    plan: Optional[ExecutionPlan] = None
    # the user's approval is stored in the user approval model
    user_approval: Optional[bool] = None
    # the step results are stored in the step result model
    step_results: List[StepResult] = Field(default_factory=list)
    # the operation complete is stored in the operation complete model
    operation_complete: bool = False
    operation_success: bool = False
    final_message: Optional[str] = None
    lessons_learned: List[str] = Field(
        default_factory=list, description="key git concepts the user learned"
    )
    # the recovery needed is a boolean that indicates whether the user needs help recovering from an error
    recovery_needed: bool = Field(
        False, description="whether user needs help recovering from an error"
    )
