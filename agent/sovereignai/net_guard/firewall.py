"""
firewall.py — OS-level egress block helpers.

The actual firewall rules are applied by scripts/install.sh (Linux) and
scripts/install.ps1 (Windows). This module:
  - Checks if rules are active
  - Applies rules programmatically on Linux (nftables/iptables)
  - Documents what a Windows admin must do manually
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_firewall_status() -> dict[str, object]:
    """Check if egress firewall rules are active."""
    system = platform.system()

    if system == "Linux":
        return _check_linux()
    elif system == "Windows":
        return _check_windows()
    elif system == "Darwin":
        return _check_macos()
    else:
        return {"status": "unknown", "system": system, "message": "Unsupported OS"}


def apply_firewall(dry_run: bool = True) -> bool:
    """
    Apply egress firewall rules. Returns True if successful.
    Only fully implemented on Linux. Windows/macOS require manual setup.
    """
    system = platform.system()

    if system == "Linux":
        return _apply_linux(dry_run=dry_run)
    else:
        print(f"\n⚠  Automatic firewall setup is only available on Linux.")
        print(f"   On {system}, configure your OS-level firewall manually.")
        print(f"   See HOW_TO_USE.md §Network Isolation for instructions.\n")
        return False


def _check_linux() -> dict[str, object]:
    """Check if nftables or iptables rules blocking egress are active."""
    if shutil.which("nft"):
        try:
            result = subprocess.run(
                ["nft", "list", "ruleset"],
                capture_output=True, text=True, timeout=5
            )
            has_rules = "sovai" in result.stdout or "drop" in result.stdout
            return {
                "status": "active" if has_rules else "not_configured",
                "system": "Linux",
                "tool": "nftables",
                "message": "nftables rules active" if has_rules else "No sovai nftables rules found. Run scripts/install.sh",
            }
        except Exception:
            pass

    if shutil.which("iptables"):
        try:
            result = subprocess.run(
                ["iptables", "-L", "OUTPUT", "-n"],
                capture_output=True, text=True, timeout=5
            )
            has_rules = "DROP" in result.stdout or "REJECT" in result.stdout
            return {
                "status": "active" if has_rules else "not_configured",
                "system": "Linux",
                "tool": "iptables",
                "message": "iptables rules found" if has_rules else "No DROP rules in OUTPUT chain. Run scripts/install.sh",
            }
        except Exception:
            pass

    return {
        "status": "not_configured",
        "system": "Linux",
        "message": "No firewall tool found. Run: sudo apt install nftables",
    }


def _check_windows() -> dict[str, object]:
    """Check Windows Defender Firewall outbound rules."""
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=SovereignAI-Egress-Block"],
            capture_output=True, text=True, timeout=5
        )
        if "SovereignAI" in result.stdout:
            return {
                "status": "active",
                "system": "Windows",
                "message": "Windows Firewall outbound block rule is active.",
            }
    except Exception:
        pass
    return {
        "status": "not_configured",
        "system": "Windows",
        "message": (
            "No SovereignAI firewall rule found. "
            "Run scripts/install.ps1 as Administrator, or see HOW_TO_USE.md."
        ),
    }


def _check_macos() -> dict[str, object]:
    return {
        "status": "not_configured",
        "system": "macOS",
        "message": "macOS: use pf (Packet Filter) to block egress. See HOW_TO_USE.md.",
    }


def _apply_linux(dry_run: bool = True) -> bool:
    """Apply nftables egress block on Linux."""
    nftables_rules = """
table inet sovai_guard {
    chain output {
        type filter hook output priority 0; policy accept;

        # Allow loopback
        oif lo accept

        # Allow established/related connections (needed for Ollama)
        ip daddr 127.0.0.1 accept
        ip6 daddr ::1 accept

        # Drop everything else outbound (log first)
        log prefix "SOVAI-BLOCKED: " flags all counter drop
    }
}
"""
    if dry_run:
        print("DRY RUN — would apply these nftables rules:")
        print(nftables_rules)
        return True

    if not shutil.which("nft"):
        print("nft not found. Install: sudo apt install nftables")
        return False

    try:
        proc = subprocess.run(
            ["nft", "-f", "-"],
            input=nftables_rules,
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            print("✅  nftables egress block applied.")
            return True
        else:
            print(f"❌  nftables error: {proc.stderr}")
            return False
    except Exception as e:
        print(f"❌  Failed to apply firewall: {e}")
        return False

