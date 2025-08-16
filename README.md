# ASD

ASD is a natural language Git assistant for the terminal. It translates plain English instructions into Git commands, helping you manage branches, histories, and merges safely and efficiently.

![ASD in action](images/example.png "Example Usage")

## Why ASD?

- I struggled with Git’s commands and conflicts.
- I wanted a simple, transparent tool—no magic—just clear steps.

## Features

- Translate English instructions into Git commands.
- Guide complex workflows with best-practice suggestions.
- Visualize commit graphs and branch histories.
- Offer safety checks and recovery guidance for risky operations.

## Getting Started

##### Installation

From PyPI:

```bash
pip install git-asd
```

Or directly from GitHub:

```bash
pip install git+https://github.com/adikuma/asd.git
```

##### Launch

```bash
asd
```

This opens ASD’s interactive terminal interface. Enter any Git task in plain English.

## Workflow

Here’s a quick look at the five-step process inside ASD:

```mermaid
flowchart LR
    Start([Start]) --> Analyze[Analyze Git Context]
    Analyze --> Intent[Parse User Intent]
    Intent --> Plan[Generate Execution Plan]
    Plan --> Review[Review Plan & Status]
    Review --> Execute[Execute Commands]
    Execute --> End([End])
```

1. **Analyze Git Context**: Examine `git status` to capture your repository’s state.
2. **Parse User Intent**: Turn your English request into a structured plan.
3. **Generate Execution Plan**:Create a safe list of Git commands.
4. **Review Plan & Status**: Inspect the plan and current status.
5. **Execute Commands**: Run each step with your approval and mini-lessons.

## Roadmap

ASD is an early project **with plenty of room for improvement**. I would love to have people test it, report issues, and suggest features so I can refine and expand its capabilities.

Contributions and feedback are welcome. Please open an issue or submit a pull request.

## Contribution Guidelines

This is my general contribution process; I like to keep it simple—sorry about that :)

| Topic                   | Guidelines                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Branching Strategy      | `feature/` for new features (e.g., `feature/add-login-command`), `fix/` for bug fixes (e.g., `fix/handle-empty-input`). |
| Code Formatting         | Use [ruff] for formatting. Run `ruff format .` before pushing.                                                                |
| Code Style              | Keep comments lowercase; use `# NOTE:` or `# TODO:` for import-related comments.                                            |
| Commit Messages         | Follow[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.                                        |
| Pull Requests & Merging | Create a PR; merging to `main` requires ≥1 collaborator approval; use **squash merge**.                                |
| Creativity              | Feel free to experiment and innovate.                                                                                           |
