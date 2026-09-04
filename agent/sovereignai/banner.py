"""
banner.py — ASCII art + color gradient renderer for SovereignAI.

Renders the startup splash screen. The literal ASCII art is hard-coded so it
renders identically on any machine even without pyfiglet installed.
"""
from __future__ import annotations

from rich.console import Console
from rich.text import Text
from rich.style import Style
from sovereignai.config import get_config

# Hard-coded art — never changes on any machine, even without pyfiglet.
_BANNER_ART = """\
██████╗  █████╗ ███████╗████████╗██╗ █████╗ ███╗   ██╗
██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██║██╔══██╗████╗  ██║
██████╔╝███████║███████╗   ██║   ██║███████║██╔██╗ ██║
██╔══██╗██╔══██║╚════██║   ██║   ██║██╔══██║██║╚██╗██║
██████╔╝██║  ██║███████║   ██║   ██║██║  ██║██║ ╚████║
╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝"""

_SUBTITLE = "            B A S T I A N   A I"
_VERSION_LINE_LOCAL  = "   sovereign agent · v0.1.0 · 🔒 LOCAL / AIR-GAPPED"
_VERSION_LINE_API    = "   sovereign agent · v0.1.0 · 🌐 API MODE (router & embeddings stay local)"
_VERSION_LINE_BREACH = "   sovereign agent · v0.1.0 · 🔓 UNEXPECTED EGRESS DETECTED"

_ACCENT_TOP    = "#5FA8D3"
_ACCENT_BOT    = "#2E5A7A"
_SUBTITLE_COL  = "#6C7A89"
_AIRGAP_AMBER  = "#D9A441"
_BREACH_RED    = "#D94141"   # distinct from amber — a real breach should not look like routine API mode


def _select_version_line(mode: str) -> tuple[str, str]:
    """mode: 'local' | 'api' | 'breach' → (line text, color)."""
    if mode == "breach":
        return _VERSION_LINE_BREACH, _BREACH_RED
    if mode == "api":
        return _VERSION_LINE_API, _AIRGAP_AMBER
    return _VERSION_LINE_LOCAL, _AIRGAP_AMBER


def get_banner_text(mode: str = "local") -> list[Text]:
    lines_art = _BANNER_ART.splitlines()
    result: list[Text] = []
    for i, line in enumerate(lines_art):
        ratio = i / max(len(lines_art) - 1, 1)
        result.append(_gradient_line(line, ratio))

    subtitle = Text(_SUBTITLE)
    subtitle.stylize(Style(color=_SUBTITLE_COL, bold=False))
    result.append(subtitle)

    version_str, color = _select_version_line(mode)
    version = Text(version_str)
    version.stylize(Style(color=color, bold=True))
    result.append(version)
    return result


def get_banner_str() -> str:
    return "\n".join([_BANNER_ART, _SUBTITLE, _VERSION_LINE_LOCAL])


def print_banner(mode: str = "local") -> None:
    console = Console()
    for line in get_banner_text(mode):
        console.print(line)
