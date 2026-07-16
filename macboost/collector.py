"""System metrics collector for macOS."""
from __future__ import annotations

import os
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

# Aplikasi yang dimonitor khusus (OpenCode, Brave, Zed)
MONITORED_APPS = ["OpenCode", "Brave Browser", "Zed"]

# Lokasi umum SQLite DB per aplikasi (diikuti urutan pencarian)
APP_DB_PATHS = {
    "OpenCode": [
        os.path.expanduser("~/.config/opencode/opencode.db"),
        os.path.expanduser("~/.opencode.db"),
    ],
    "Brave Browser": [
        os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History"),
        os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Bookmarks"),
    ],
    "Zed": [
        os.path.expanduser("~/Library/Application Support/Zed/settings.json"),
        os.path.expanduser("~/.config/zed/zed.db"),
    ],
}


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
    # default sampler (tanpa -s) tetap keluarkan "CPU die temperature"
    out = _run("sudo powermetrics -n 1 2>/dev/null")
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


def get_storage() -> list[str]:
    """Return list baris 'size used avail capacity mount'."""
    out = _run("df -h / /System/Volumes/Data 2>/dev/null")
    lines = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            lines.append(f"{parts[0]}: {parts[1]} used / {parts[3]} free ({parts[4]})")
    return lines or ["?"]


def get_ram() -> str:
    out = _run("vm_stat")
    # hitung page berdasarkan page size 4096
    pages = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = "".join(filter(str.isdigit, v))
            if v:
                pages[k.strip()] = int(v)
    ps = 4096
    free = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
    active = pages.get("Pages active", 0)
    inactive = pages.get("Pages inactive", 0)
    wired = pages.get("Pages wired down", 0)
    comp = pages.get("Pages occupied by compressor", 0)
    used = (active + inactive + wired + comp) * ps
    free_b = free * ps
    total = used + free_b
    if total == 0:
        return "?"
    used_gb = used / (1024 ** 3)
    total_gb = total / (1024 ** 3)
    pct = int(used / total * 100)
    return f"{used_gb:.1f} GB / {total_gb:.1f} GB ({pct}%)"


def get_running_apps() -> list[str]:
    """Aplikasi GUI yang jalan (from osascript)."""
    out = _run('osascript -e "tell application \\"System Events\\" to get name of every process whose background only is false"')
    return [a.strip() for a in out.replace(",", "\n").split("\n") if a.strip()]


def get_running_services() -> list[str]:
    """LaunchAgent + LaunchDaemon yang loaded."""
    out = _run("launchctl list | grep -v '^-' | awk '{print $3}' | grep -v '^$'")
    svcs = []
    for s in out.splitlines():
        s = s.strip()
        if s and s != "Label":
            svcs.append(s)
    return svcs


def get_network() -> dict:
    """IP lokal (en0) + IP publik + interface aktif."""
    local = _run("ipconfig getifaddr en0").strip() or _run("ipconfig getifaddr en1").strip() or "?"
    # publik (timeout cepat)
    pub = _run("curl -s --max-time 5 ifconfig.me").strip() or "?"
    active_if = _run("route -n get default 2>/dev/null | awk '/interface:/{print $2}'").strip() or "?"
    return {"local": local, "public": pub, "interface": active_if}


def get_battery_detail() -> dict:
    out = _run("system_profiler SPPowerDataType 2>/dev/null")
    detail = {"cycle": "?", "condition": "?", "health": "?"}
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Cycle Count"):
            detail["cycle"] = s.split(":")[-1].strip()
        elif s.startswith("Condition"):
            detail["condition"] = s.split(":")[-1].strip()
        elif "Maximum Capacity" in s or "State of Charge" in s:
            detail["health"] = s.split(":")[-1].strip()
    return detail


def get_cpu_info() -> str:
    out = _run("sysctl -n machdep.cpu.brand_string 2>/dev/null").strip()
    return out or "?"


def collect_full() -> dict:
    m = collect()
    apps = get_running_apps()
    svcs = get_running_services()
    net = get_network()
    batt_d = get_battery_detail()
    return {
        "battery_pct": m.battery_pct,
        "battery_status": m.battery_status,
        "battery_cycle": batt_d["cycle"],
        "battery_condition": batt_d["condition"],
        "battery_health": batt_d["health"],
        "cpu_temp_c": m.cpu_temp_c,
        "cpu": get_cpu_info(),
        "load_avg": m.load_avg,
        "ram": get_ram(),
        "storage": get_storage(),
        "heavy_apps": m.heavy_apps,
        "running_apps": apps,
        "running_services": svcs,
        "network": net,
    }


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


def sqlite_info(path: str) -> str:
    """Ambil info ringkas SQLite DB: ukuran + jumlah tabel (bila sqlite3 ada)."""
    if not os.path.exists(path):
        return "tidak ada"
    size = os.path.getsize(path)
    size_kb = size / 1024
    if size_kb >= 1024:
        size_str = f"{size_kb / 1024:.1f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"
    info = f"{size_str}"
    try:
        out = _run(f'sqlite3 "{path}" ".tables"')
        tables = [t for t in out.split() if t]
        if tables:
            info += f" | {len(tables)} tabel"
    except Exception:
        pass
    return info


def monitor_app(app_name: str) -> dict:
    """Kumpulkan status + info SQLite untuk satu aplikasi yang dimonitor."""
    running = app_running(app_name)
    pid = _run(f'pgrep -f "{app_name}"').strip().split("\n")[0] if running else ""
    cpu_mem = ""
    if pid:
        # ambil %CPU & RSS (bytes) dari ps
        ps = _run(f"ps -o %cpu,rss -p {pid} 2>/dev/null").strip().splitlines()
        if len(ps) > 1:
            parts = ps[1].split()
            if len(parts) == 2:
                cpu = parts[0]
                rss_mb = int(parts[1]) / 1024
                cpu_mem = f"CPU {cpu}% | RAM {rss_mb:.0f} MB"
    dbs = []
    for p in APP_DB_PATHS.get(app_name, []):
        dbs.append((os.path.basename(p), sqlite_info(p)))
    return {
        "name": app_name,
        "running": running,
        "pid": pid,
        "cpu_mem": cpu_mem,
        "dbs": dbs,
    }


def monitor_apps() -> list[dict]:
    """Return list status semua aplikasi yang dimonitor."""
    return [monitor_app(a) for a in MONITORED_APPS]


def monitor_apps_text() -> str:
    """Format laporan monitoring ke teks Markdown."""
    lines = ["🖥️ *MONITORING APLIKASI*\n"]
    for d in monitor_apps():
        status = "🟢 ON " if d["running"] else "⚪ OFF"
        head = f"{status} *{d['name']}*"
        if d["running"] and d["pid"]:
            head += f" (PID {d['pid']})"
        lines.append(head)
        if d["running"] and d["cpu_mem"]:
            lines.append(f"   └ {d['cpu_mem']}")
        if d["dbs"]:
            db_line = "   └ DB: " + " | ".join(f"{n}: {i}" for n, i in d["dbs"])
            lines.append(db_line)
        lines.append("")
    return "\n".join(lines).rstrip()


# ----- Git update checker -----
def git_repo_dir() -> str:
    """Return direktori repo git (parent macboost/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_commit() -> str:
    out = _run(f'cd "{git_repo_dir()}" && git rev-parse HEAD').strip()
    return out or "?"


def get_remote_commit() -> str:
    out = _run(f'cd "{git_repo_dir()}" && git rev-parse origin/main').strip()
    return out or "?"


def fetch_remote() -> None:
    _run(f'cd "{git_repo_dir()}" && git fetch origin --quiet 2>/dev/null')


def check_update() -> dict:
    """Cek apakah ada commit baru di remote vs lokal.

    Return: {"behind": bool, "local": str, "remote": str, "commits": int}
    """
    fetch_remote()
    local = get_local_commit()
    remote = get_remote_commit()
    behind = False
    commits = 0
    if local and remote and local != remote:
        behind = True
        revs = _run(
            f'cd "{git_repo_dir()}" && git rev-list --count {local}..{remote}'
        ).strip()
        try:
            commits = int(revs)
        except ValueError:
            commits = 0
    return {"behind": behind, "local": local, "remote": remote, "commits": commits}


def update_summary() -> str:
    """Ambil ringkasan commit baru (subject tiap commit)."""
    local = get_local_commit()
    remote = get_remote_commit()
    out = _run(
        f'cd "{git_repo_dir()}" && git log --oneline {local}..{remote}'
    ).strip()
    return out or "(tidak ada info)"
