"""
net_guard/monitor.py — Live network connection watcher.

Fixed: only flags TRUE external connections (not Windows system/loopback/link-local).
Private RFC-1918 ranges and link-local are never counted as external.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from ipaddress import ip_address, IPv4Network, IPv6Network
from typing import Callable

from sovereignai.config import get_config

# All of these are "internal" — never flag them
_INTERNAL_NETS = [
    IPv4Network("127.0.0.0/8"),     # loopback
    IPv4Network("10.0.0.0/8"),      # RFC-1918
    IPv4Network("172.16.0.0/12"),   # RFC-1918
    IPv4Network("192.168.0.0/16"),  # RFC-1918
    IPv4Network("169.254.0.0/16"),  # link-local
    IPv4Network("0.0.0.0/8"),       # unspecified
    IPv6Network("::1/128"),         # IPv6 loopback
    IPv6Network("fe80::/10"),       # IPv6 link-local
    IPv6Network("fc00::/7"),        # IPv6 unique local
]


def _is_internal(ip_str: str) -> bool:
    if not ip_str or ip_str in ("", "0.0.0.0", "::", "*"):
        return True
    try:
        addr = ip_address(ip_str)
        for net in _INTERNAL_NETS:
            if addr in net:
                return True
        return False
    except ValueError:
        return True  # unparseable → treat as internal (safe default)


@dataclass
class ConnectionRecord:
    laddr: str
    raddr: str
    status: str
    process_name: str
    pid: int | None = None
    is_sovai: bool = False


@dataclass
class MonitorState:
    connections: list[ConnectionRecord] = field(default_factory=list)
    external_attempts: int = 0
    system_external_count: int = 0
    last_checked: float = field(default_factory=time.time)
    alert: bool = False


class NetworkMonitor:
    def __init__(self) -> None:
        self._cfg = get_config()
        self._state = MonitorState()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._alert_callbacks: list[Callable[[int], None]] = []
        self._session_external = 0  # count for THIS session only (SovereignAI process only)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="sovai-netguard"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def add_alert_callback(self, cb: Callable[[int], None]) -> None:
        self._alert_callbacks.append(cb)

    def get_state(self) -> MonitorState:
        with self._lock:
            return MonitorState(
                connections=list(self._state.connections),
                external_attempts=self._state.external_attempts,
                system_external_count=self._state.system_external_count,
                last_checked=self._state.last_checked,
                alert=self._state.alert,
            )

    def _poll_loop(self) -> None:
        poll_s = self._cfg.net_guard_poll_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception:
                pass
            time.sleep(poll_s)

    def _poll_once(self) -> None:
        try:
            import psutil
        except ImportError:
            return

        conns: list[ConnectionRecord] = []
        new_session_external = 0
        system_external = 0

        # Identify SovereignAI PID and all of its subprocesses
        sovai_pids: set[int] = {os.getpid()}
        try:
            current_proc = psutil.Process(os.getpid())
            for child in current_proc.children(recursive=True):
                sovai_pids.add(child.pid)
        except Exception:
            pass

        try:
            net_conns = psutil.net_connections(kind="inet")
        except Exception:
            try:
                net_conns = psutil.net_connections(kind="tcp")
            except Exception:
                return

        for conn in net_conns:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "—"
            raddr = ""
            raddr_ip = ""
            if conn.raddr:
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
                raddr_ip = conn.raddr.ip

            is_sovai = conn.pid in sovai_pids if conn.pid else False

            # Only flag ESTABLISHED connections to true external IPs
            is_external = (
                bool(raddr_ip)
                and not _is_internal(raddr_ip)
                and conn.status == "ESTABLISHED"
            )

            if is_external:
                if is_sovai:
                    new_session_external += 1
                else:
                    system_external += 1

            proc_name = "?"
            if conn.pid:
                try:
                    proc_name = psutil.Process(conn.pid).name()
                except Exception:
                    pass

            conns.append(ConnectionRecord(
                laddr=laddr,
                raddr=raddr or "—",
                status=conn.status or "?",
                process_name=proc_name,
                pid=conn.pid,
                is_sovai=is_sovai,
            ))

        # Put SovereignAI's own connections at the top of the list
        conns.sort(key=lambda c: (not c.is_sovai, c.process_name))

        prev = self._session_external
        with self._lock:
            self._state.connections = conns
            self._state.system_external_count = system_external
            # Alert ONLY if SovereignAI itself initiated external connections
            if new_session_external > self._session_external:
                self._session_external = new_session_external
                self._state.external_attempts = new_session_external
                self._state.alert = True
            elif new_session_external == 0 and self._session_external == 0:
                self._state.external_attempts = 0
                self._state.alert = False
            self._state.last_checked = time.time()

        if self._session_external > prev:
            for cb in self._alert_callbacks:
                try:
                    cb(self._session_external)
                except Exception:
                    pass


_monitor: NetworkMonitor | None = None


def get_monitor() -> NetworkMonitor:
    global _monitor
    if _monitor is None:
        _monitor = NetworkMonitor()
    return _monitor
