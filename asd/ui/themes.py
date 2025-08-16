from rich.theme import Theme

THEME = Theme(
    {
        # primary hierarchy (titles, prompts, input labels)
        "header": "bold #3b5b76",  # deep slate blue
        "prompt": "bold #3b5b76",
        "input": "bold #3b5b76",
        # accents & content roles
        "accent": "#8fb4d8",  # soft steel blue highlight
        "command": "#e6edf3",  # high-contrast neutral for commands/output
        "info": "#a9b7c6",  # secondary copy
        "caption": "#5a6472",  # low-emphasis labels
        # feedback (kept muted; no neon)
        "success": "#8fb4d8",  # reuse accent for success
        "warning": "#b7c1cf",  # cool grey-blue caution
        "failure": "#d16d6d",  # tempered red
        "destructive": "#d16d6d",
        "loading": "#8fb4d8",
        # safety levels
        "safe": "#8fb4d8",
        "caution": "#b7c1cf",
        "risky": "#d29b6d",
        "dangerous": "#d16d6d",
        # educational cues stay cool
        "educational": "#8fb4d8",
        "concept": "#3b5b76",
        # questionary
        "choice": "#d7ba7d",
        "note": "#ff77ff",
    }
)

# simple symbols used across the ui
SYMBOLS = {
    "prompt": ">",
    "success": "+",
    "failure": "x",
    "warning": "!",
    "info": "*",
    "safety": "#",
    "education": ">",
}
