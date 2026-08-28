"""
banner.py — ASCII art + color gradient renderer for SovereignAI.

Renders the startup splash screen. The literal ASCII art is hard-coded so it
renders identically on any machine even without pyfiglet installed.
"""
from __future__ import annotations

from rich.console import Console
from rich.text import Text
from rich.style import Style


# Hard-coded art — never changes on any machine, even without pyfiglet.
_BANNER_ART = """\
███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗
██╔════╝██╔═══██╗██║   ██║██╔══██╗██║
███████╗██║   ██║██║   ██║███████║██║
╚════██║██║   ██║╚██╗ ██╔╝██╔══██║██║
███████║╚██████╔╝ ╚████╔╝ ██║  ██║██║
╚══════╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝"""

_SUBTITLE = "        S O V E R E I G N   A I"
_VERSION_LINE_ONLINE = "   air-gapped agent · v0.1.0 · 🔒 OFFLINE"
_VERSION_LINE_WARN   = "   air-gapped agent · v0.1.0 · 🔓 ONLINE-BLOCKED"

# Color scheme (spec §1 / §9.5)
_ACCENT_TOP    = "#5FA8D3"   # steel-blue top of banner
_ACCENT_BOT    = "#2E5A7A"   # deeper teal at bottom
_SUBTITLE_COL  = "#6C7A89"   # dim grey
_AIRGAP_AMBER  = "#D9A441"   # amber — air-gap / network indicator


def _gradient_line(text: str, ratio: float) -> Text:
    """Interpolate between _ACCENT_TOP and _ACCENT_BOT based on ratio (0.0–1.0)."""
    def _lerp_hex(c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    color = _lerp_hex(_ACCENT_TOP, _ACCENT_BOT, ratio)
    t = Text(text)
    t.stylize(Style(color=color, bold=True))
    return t


def get_banner_text(online: bool = False) -> list[Text]:
    """Return the full banner as a list of Rich Text lines (for Textual widgets)."""
    lines_art = _BANNER_ART.splitlines()
    result: list[Text] = []

    for i, line in enumerate(lines_art):
        ratio = i / max(len(lines_art) - 1, 1)
        result.append(_gradient_line(line, ratio))

    subtitle = Text(_SUBTITLE)
    subtitle.stylize(Style(color=_SUBTITLE_COL, bold=False))
    result.append(subtitle)

    version_str = _VERSION_LINE_WARN if online else _VERSION_LINE_ONLINE
    version = Text(version_str)
    version.stylize(Style(color=_AIRGAP_AMBER, bold=True))
    result.append(version)

    return result


def get_banner_str() -> str:
    """Return the banner as a plain string (for --version, logs, etc.)."""
    lines = [_BANNER_ART, _SUBTITLE, _VERSION_LINE_ONLINE]
    return "\n".join(lines)


def print_banner(online: bool = False) -> None:
    """Print the banner to stdout (used by CLI before TUI starts)."""
    console = Console()
    for line in get_banner_text(online):
        console.print(line)

