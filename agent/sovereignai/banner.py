"""
banner.py — ASCII art + color gradient renderer for Bastion.

Renders the startup splash screen. The literal ASCII art is hard-coded so it
renders identically on any machine even without pyfiglet installed.
"""
from __future__ import annotations

from rich.console import Console
from rich.text import Text
from rich.style import Style

# Hard-coded art for BASTION
_BANNER_ART = """\
██████╗  █████╗ ███████╗████████╗██╗ ██████╗  ███╗   ██╗
██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
██████╔╝███████║███████╗   ██║   ██║██║   ██║██╔██╗ ██║
██╔══██╗██╔══██║╚════██║   ██║   ██║██║   ██║██║╚██╗██║
██████╔╝██║  ██║███████║   ██║   ██║╚██████╔╝██║ ╚████║
╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝"""

_SUBTITLE = "            B A S T I O N   A I"

_GRADIENT_COLORS = [
    "#5FA8D3",
    "#4a90b8",
    "#3d7da0",
    "#306988",
    "#2E5A7A",
    "#2E5A7A",
]


def get_banner_text() -> list[Text]:
    lines_art = _BANNER_ART.splitlines()
    result: list[Text] = []
    for i, line in enumerate(lines_art):
        color = _GRADIENT_COLORS[min(i, len(_GRADIENT_COLORS) - 1)]
        t = Text(line)
        t.stylize(Style(color=color, bold=True))
        result.append(t)

    subtitle = Text(_SUBTITLE)
    subtitle.stylize(Style(color="#6C7A89", bold=False))
    result.append(subtitle)
    return result


def get_banner_str() -> str:
    return "\n".join([_BANNER_ART, _SUBTITLE])


def print_banner(mode: str = "local") -> None:
    console = Console()
    for line in get_banner_text():
        console.print(line)
