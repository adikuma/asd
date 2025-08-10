from rich.theme import Theme

THEME = Theme(
    {
        # core ui styles
        "header": "bold orange1",
        "accent": "bright_yellow",
        "prompt": "bold orange1",
        "input": "bold orange1",
        "info": "grey70",
        "loading": "plum3",
        # git command and safety styles
        "command": "bright_white",
        "success": "green3",
        "failure": "red1",
        "warning": "yellow3",
        "destructive": "red1",
        # educational content
        "educational": "bright_yellow",
        "concept": "orange1",
        # safety levels
        "safe": "green3",
        "caution": "yellow3",
        "risky": "orange1",
        "dangerous": "red1",
        "caption": "grey50",
    }
)

SYMBOLS = {
    "prompt": ">",
    "success": "+",
    "failure": "x",
    "warning": "!",
    "info": "*",
    "safety": "#",
    "education": ">",
}
