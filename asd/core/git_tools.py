import os
import subprocess
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .costs import UsageCallback, get_active_model_provider
from .models import GitStatus, SafetyLevel


# running git commands and capturing the output
# using the subprocess module to run the commands
def run_git_command(cmd: str, suppress_errors: bool = False) -> Dict[str, any]:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "command timed out",
            "returncode": -1,
        }
    except Exception as e:
        if not suppress_errors:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
        return {"success": False, "stdout": "", "stderr": "", "returncode": -1}


# getting the git status of the repo
def get_git_status() -> GitStatus:
    # using the run git function and running the git rev-parse --is-inside-work-tree command to check if the current directory is a git repository
    is_repo_result = run_git_command(
        "git rev-parse --is-inside-work-tree", suppress_errors=True
    )
    # if the current directory is not a git repository, the git status is set to false
    if not is_repo_result["success"] or is_repo_result["stdout"] != "true":
        return GitStatus(is_repo=False)

    # run the git branch --show-current command to get the current branch
    branch_result = run_git_command("git branch --show-current")
    # if the current branch is not found, the current branch is set to HEAD
    current_branch = branch_result["stdout"] or "HEAD"

    # run the git status --porcelain command to get the status of the repo
    porcelain_result = run_git_command("git status --porcelain")
    # if the git status command fails, the porcelain lines are set to an empty list
    porcelain_lines = (
        porcelain_result["stdout"].splitlines() if porcelain_result["success"] else []
    )

    # parsing the porcelain lines to get the staged, modified, and untracked files
    staged, modified, untracked = [], [], []
    for line in porcelain_lines:
        if len(line) < 3:
            continue
        index_status = line[0]
        worktree_status = line[1]
        filepath = line[3:].strip()

        if index_status in "AMDRC":
            staged.append(filepath)

        if worktree_status in "MD":
            modified.append(filepath)
        elif index_status == "?" and worktree_status == "?":
            untracked.append(filepath)

    # run the git status --branch --porcelain command to get the ahead and behind commits
    ahead = behind = 0
    # run the git status --branch --porcelain command to get the ahead and behind commits
    status_result = run_git_command("git status --branch --porcelain")
    # if the git status command fails, the ahead and behind commits are set to 0
    if status_result["success"] and status_result["stdout"]:
        # get the first line of the status result
        first_line = status_result["stdout"].splitlines()[0]
        # if the first line contains ahead, try to get the number of ahead commits
        if "[ahead" in first_line:
            try:
                ahead_part = first_line.split("[ahead ")[1].split("]")[0]
                if "," in ahead_part:
                    ahead = int(ahead_part.split(",")[0])
                else:
                    ahead = int(ahead_part)
            except (IndexError, ValueError):
                ahead = 0
        if "behind" in first_line:
            try:
                behind_part = first_line.split("behind ")[1].split("]")[0]
                if "," in behind_part:
                    behind = int(behind_part.split(",")[0])
                else:
                    behind = int(behind_part)
            except (IndexError, ValueError):
                behind = 0

    # run the git ls-files --unmerged command to check for conflicts (for merge conflicts if any)
    conflicts_result = run_git_command("git ls-files --unmerged")
    has_conflicts = (
        bool(conflicts_result["stdout"]) if conflicts_result["success"] else False
    )

    # run the git rev-list --count HEAD command to get the total number of commits
    commit_count_result = run_git_command("git rev-list --count HEAD")
    total_commits = 0
    # if the git rev-list command fails, the total commits are set to 0
    if commit_count_result["success"]:
        try:
            total_commits = int(commit_count_result["stdout"])
        except ValueError:
            total_commits = 0

    # run the git remote command to check if the repo has a remote
    remote_result = run_git_command("git remote")
    # if the git remote command fails, the remote is set to false
    has_remote = bool(remote_result["stdout"]) if remote_result["success"] else False
    # if the remote is found, the remote name is set to the first remote name
    remote_name = remote_result["stdout"].split("\n")[0] if has_remote else ""

    last_commit_hash = ""
    last_commit_message = ""
    # run the git log -1 --format='%H|%s' command to get the last commit hash and message
    commit_info_result = run_git_command("git log -1 --format='%H|%s'")
    if commit_info_result["success"] and commit_info_result["stdout"]:
        try:
            # split the commit info result into a list of two elements
            hash_msg = commit_info_result["stdout"].split("|", 1)
            # set the last commit hash to the first element of the list
            last_commit_hash = hash_msg[0][:8]  # short hash
            # set the last commit message to the second element of the list
            last_commit_message = hash_msg[1] if len(hash_msg) > 1 else ""
        except IndexError:
            pass

    # run the git stash list command to get the number of stashed changes
    stash_result = run_git_command("git stash list")
    stash_count = (
        len(stash_result["stdout"].splitlines()) if stash_result["success"] else 0
    )

    # get the total number of uncommitted changes
    uncommitted_changes = len(staged) + len(modified)

    # return the git status with all the information gathered
    return GitStatus(
        is_repo=True,
        current_branch=current_branch,
        staged=staged,
        modified=modified,
        untracked=untracked,
        ahead=ahead,
        behind=behind,
        conflicts=has_conflicts,
        total_commits=total_commits,
        uncommitted_changes=uncommitted_changes,
        has_remote=has_remote,
        remote_name=remote_name,
        last_commit_hash=last_commit_hash,
        last_commit_message=last_commit_message,
        stash_count=stash_count,
    )


# using the git diff --staged command to get the diff of the staged changes
# if the git diff command fails, the diff is set to None
def get_git_diff_analysis() -> Optional[str]:
    diff_result = run_git_command("git diff --staged")
    if not diff_result["success"] or not diff_result["stdout"]:
        return None
    return diff_result["stdout"]


# the idea is to check the prerequisites for a command
def check_git_prerequisites(command: str, git_status: GitStatus) -> List[str]:
    issues = []
    cmd_lower = command.lower()

    # if the command is a commit and no files are staged, add a warning
    if "commit" in cmd_lower and not git_status.staged:
        issues.append("no files are staged for commit - use 'git add' first")

    # if the command is a push and no remote is configured, add a warning
    if "push" in cmd_lower and not git_status.has_remote:
        issues.append("no remote repository configured - add one with 'git remote add'")

    # if the command is a merge and there are conflicts, add a warning
    if "merge" in cmd_lower and git_status.conflicts:
        issues.append("resolve existing merge conflicts before merging")

    # if the command is a pull and there are uncommitted changes, add a warning
    if "pull" in cmd_lower and git_status.uncommitted_changes > 0:
        issues.append("commit or stash changes before pulling to avoid conflicts")

    # if the command is a rebase and there are uncommitted changes, add a warning
    if "rebase" in cmd_lower and git_status.uncommitted_changes > 0:
        issues.append("commit or stash changes before rebasing")

    return issues


class CommitMessage(BaseModel):
    message: str = Field(
        ...,
        description="ai-generated commit message following conventional commit format",
    )
    explanation: str = Field(..., description="why this commit message was chosen")


# using llm to generate a commit message
# using the conventional commit format to generate the commit message
# FIXED: the model now uses the same model as the rest of the application
def get_llm():
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "o4-mini"), api_key=os.getenv("OPENAI_API_KEY")
    )


def generate_commit_message(diff: str) -> Tuple[str, str]:
    llm = get_llm()

    mapper = llm.with_structured_output(CommitMessage)

    system_prompt = """analyze the git diff and create a conventional commit message.

    conventional commit format: <type>: <description>

    types:
    - feat: new feature
    - fix: bug fix  
    - docs: documentation
    - style: formatting changes
    - refactor: code restructuring
    - test: adding tests
    - chore: maintenance tasks

    examples:
    - feat: add user authentication
    - fix: resolve login timeout issue  
    - docs: update installation guide
    - refactor: simplify validation logic

    create a concise, imperative message that describes the most significant change."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"git diff:\n{diff}"),
    ]

    provider, model = get_active_model_provider()
    result = mapper.invoke(
        messages,
        config={"callbacks": [UsageCallback(provider, model)]},
    )
    return result.message, result.explanation
