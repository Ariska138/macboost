#!/usr/bin/env python3
"""
mac-telegram-monitor.py
Monitoring & kontrol MacBook via Telegram.
Fitur: alert baterai/suhu, matikan app remote, shutdown/restart.

SETUP:
  1. Isi BOT_TOKEN dan CHAT_ID di bawah (atau via env var).
  2. chmod +x mac-telegram-monitor.py
  3. Jalankan via LaunchAgent (lihat com.user.mactmon.plist).

Perintah dari Telegram:
  status      -> laporan baterai/suhu/beban
  kill <app>  -> quit app (misal: kill OpenCode)
  killall     -> quit app berat (OpenCode, Brave Browser, WhatsApp)
  shutdown    -> matikan Mac
  restart     -> restart Mac
  off         -> alias shutdown
  help        -> daftar perintah

Keamanan: hanya CHAT_ID di atas yang direspon.
"""

import os
import json
import time
import subprocess
import urllib.request
import urllib.parse

BOT_TOKEN = os.environ.get("MACTMON_BOT_TOKEN", "ISI_BOT_TOKEN_DISINI")
CHAT_ID = os.environ.get("MACTMON_CHAT_ID", "ISI_CHAT_ID_DISINI")

HEAVY_APPS = ["OpenCode", "Brave Browser", "WhatsApp"]

BATTERY_ALERT_THRESHOLD = 20   # % di bawah ini -> alert
TEMP_ALERT_THRESHOLD = 80      # derajat C di atas ini -> alert

POLL_INTERVAL = 30             # detik antar cek
COMMAND_TIMEOUT = 20           # detik long-poll Telegram

last_battery_alert = 100
last_temp_alert = 0
offset = 0


def send_msg(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[send_msg error] {e}")


def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def get_battery():
    """Return (pct:int, status:str)"""
    out = run("pmset -g batt").stdout
    for line in out.splitlines():
        if "Internal" in line:
            parts = [p.strip() for p in line.split(";")]
            pct = int("".join(filter(str.isdigit, parts[0])))
            status = parts[2] if len(parts) > 2 else "?"
            return pct, status
    return 0, "unknown"


def get_temp():
    """Return CPU die temperature in C (0 jika gagal)."""
    out = run("sudo powermetrics -n 1 -s cpu_power 2>/dev/null").stdout
    for line in out.splitlines():
        if "CPU die temperature" in line:
            digits = "".join(filter(lambda c: c.isdigit() or c == ".", line.split(":")[-1]))
            try:
                return float(digits)
            except ValueError:
                return 0.0
    return 0.0


def get_load():
    out = run("uptime").stdout
    if "load averages:" in out:
        return out.split("load averages:")[1].strip().split()[0]
    return "?"


def app_running(name):
    return run(f'pgrep -f "{name}"').returncode == 0


def kill_app(name):
    if not app_running(name):
        return f"App '{name}' tidak jalan."
    run(f'osascript -e \'quit app "{name}"\'')
    time.sleep(2)
    run(f'pkill -f "{name}"')
    return f"App '{name}' dimatikan."


def handle_command(text):
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "status":
        pct, status = get_battery()
        temp = get_temp()
        send_msg(f"📊 STATUS MAC\nBaterai: {pct}% ({status})\nSuhu CPU: {temp}°C\nLoad avg: {get_load()}")
    elif cmd == "kill":
        if not arg:
            send_msg("Pakai: kill <nama app> (misal: kill OpenCode)")
        else:
            send_msg("✅ " + kill_app(arg))
    elif cmd == "killall":
        msg = ""
        for a in HEAVY_APPS:
            if app_running(a):
                msg += "\n" + kill_app(a)
        send_msg("🧹 Killall app berat:" + (msg or "\n(tidak ada yang jalan)"))
    elif cmd in ("shutdown", "off"):
        send_msg("🔌 Mematikan Mac...")
        run("sudo shutdown -h now")
    elif cmd == "restart":
        send_msg("🔄 Restart Mac...")
        run("sudo shutdown -r now")
    else:
        send_msg(
            "Perintah:\n"
            "status - laporan\n"
            "kill <app> - matikan app\n"
            "killall - matikan app berat\n"
            "shutdown/off - matikan Mac\n"
            "restart - restart Mac"
        )


def poll_commands():
    global offset
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout={COMMAND_TIMEOUT}&offset={offset}"
    try:
        with urllib.request.urlopen(url, timeout=COMMAND_TIMEOUT + 5) as r:
            data = json.load(r)
    except Exception as e:
        print(f"[poll error] {e}")
        return

    for upd in data.get("result", []):
        offset = upd["update_id"] + 1
        msg = upd.get("message", {})
        chat = msg.get("chat", {})
        text = msg.get("text", "")
        if str(chat.get("id")) == str(CHAT_ID) and text:
            handle_command(text)


def main():
    send_msg("🤖 Mac Monitor aktif. Kirim 'help' untuk daftar perintah.")
    while True:
        # alert otomatis
        pct, status = get_battery()
        temp = get_temp()

        if 0 < pct <= BATTERY_ALERT_THRESHOLD and pct < last_battery_alert:
            send_msg(f"⚠️ BATTERAI RENDAH: {pct}% ({status})")
        globals()["last_battery_alert"] = pct

        if temp >= TEMP_ALERT_THRESHOLD and temp > last_temp_alert:
            send_msg(f"🌡️ SUHU PANAS: {temp}°C")
        globals()["last_temp_alert"] = temp

        poll_commands()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
