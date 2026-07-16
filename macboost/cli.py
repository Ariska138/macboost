"""CLI entrypoint for MacBoost."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from . import collector
from .bot import Bot
from .web import run_dashboard


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def main():
    load_dotenv()
    token = _env("MACTMON_BOT_TOKEN")
    chat_id = _env("MACTMON_CHAT_ID")

    if not token or token == "ISI_BOT_TOKEN_DISINI":
        print("ERROR: set MACTMON_BOT_TOKEN & MACTMON_CHAT_ID di .env")
        print("Lihat .env.example")
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if mode == "bot":
        Bot(token, chat_id).run()
    elif mode == "web":
        port = int(_env("MACBOOST_WEB_PORT", "8080"))
        print(f"Dashboard: http://127.0.0.1:{port}")
        run_dashboard(port=port)
    elif mode == "status":
        m = collector.collect()
        print(f"Battery: {m.battery_pct}% ({m.battery_status})")
        print(f"Temp: {m.cpu_temp_c}C")
        print(f"Load: {m.load_avg}")
        print(f"Heavy apps: {m.heavy_apps}")
    elif mode == "info":
        d = collector.collect_full()
        print(f"CPU: {d['cpu']}")
        print(f"Battery: {d['battery_pct']}% {d['battery_status']} "
              f"(cycle {d['battery_cycle']}, {d['battery_condition']})")
        print(f"Temp: {d['cpu_temp_c']}C | Load: {d['load_avg']}")
        print(f"RAM: {d['ram']}")
        print(f"Storage: {d['storage']}")
        print(f"Network: {d['network']}")
        print(f"Apps ({len(d['running_apps'])}): {d['running_apps']}")
        print(f"Services ({len(d['running_services'])}): {d['running_services']}")
    else:
        print("Usage: macboost [bot|web|status]")


if __name__ == "__main__":
    main()
