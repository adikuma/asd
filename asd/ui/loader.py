from typing import Optional

from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner

from .display import console as _loader_console

_current_live: Optional[Live] = None


def _render_panel(message: str):
    row = Columns([Spinner("dots"), Align.left(message)], expand=True, equal=False)
    return Panel(row, border_style="accent", style="on #0b1116", padding=(0, 1))


def start_loader(message: str):
    global _current_live
    stop_loader()
    _current_live = Live(
        _render_panel(message),
        console=_loader_console,
        refresh_per_second=16,
        transient=True,  # disappears on stop()
    )
    _current_live.start()


def stop_loader():
    global _current_live
    if _current_live is not None:
        try:
            _current_live.stop()
        finally:
            _current_live = None
