"""System metrics collector for macOS."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class Metrics:
    battery_pct: int
    battery_status: str
    cpu_temp_c: float
    load_avg: str
    heavy_apps: list[str]


HEAVY_APPS = ["OpenCode", "Brave Browser", "WhatsApp"]


def _run(cmd: str) -> str:
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        ).stdout
    except Exception:
        return ""


def get_battery() -> tuple[int, str]:
    out = _run("pmset -g batt")
    for line in out.splitlines():
        if "InternalBattery" in line:
            # contoh: -InternalBattery-0 (id=..)  100%; charged; 0:00 remaining present: true
            parts = [p.strip() for p in line.split(";")]
            pct = int("".join(filter(str.isdigit, parts[0].split(")")[-1])))
            status = parts[1] if len(parts) > 1 else "?"
            return pct, status
    return 0, "unknown"


def get_temp() -> float:
    out = _run("sudo powermetrics -n 1 -s cpu_power 2>/dev/null")
    for line in out.splitlines():
        if "CPU die temperature" in line:
            digits = "".join(c for c in line.split(":")[-1] if c.isdigit() or c == ".")
            try:
                return float(digits)
            except ValueError:
                return 0.0
    return 0.0


def get_load() -> str:
    out = _run("uptime")
    if "load averages:" in out:
        return out.split("load averages:")[1].strip().split()[0]
    return "?"


def app_running(name: str) -> bool:
    return _run(f'pgrep -f "{name}"').strip() != ""


def running_heavy_apps() -> list[str]:
    return [a for a in HEAVY_APPS if app_running(a)]


def collect() -> Metrics:
    pct, status = get_battery()
    return Metrics(
        battery_pct=pct,
        battery_status=status,
        cpu_temp_c=get_temp(),
        load_avg=get_load(),
        heavy_apps=running_heavy_apps(),
    )


def kill_app(name: str) -> str:
    if not app_running(name):
        return f"App '{name}' tidak jalan."
    _run(f'osascript -e \'quit app "{name}"\'')
    import time
    time.sleep(2)
    _run(f'pkill -f "{name}"')
    return f"App '{name}' dimatikan."


def kill_all_heavy() -> str:
    msgs = []
    for a in HEAVY_APPS:
        if app_running(a):
            msgs.append(kill_app(a))
    return "\n".join(msgs) if msgs else "(tidak ada app berat jalan)"


def shutdown() -> None:
    _run("sudo shutdown -h now")


def restart() -> None:
    _run("sudo shutdown -r now")
