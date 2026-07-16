"""Telegram bot handler for MacBoost."""
from __future__ import annotations

import os
import time

import requests

from . import collector

POLL_INTERVAL = 5
COMMAND_TIMEOUT = 30
BATTERY_ALERT = 20
TEMP_ALERT = 80


def _keyboard():
    kb = [
        [{"text": "📊 Status", "callback_data": "status"}],
        [
            {"text": "🧹 Kill All", "callback_data": "killall"},
            {"text": "⏻ Shutdown", "callback_data": "shutdown"},
            {"text": "🔄 Restart", "callback_data": "restart"},
        ],
    ]
    return {"inline_keyboard": kb}


class Bot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = str(chat_id)
        self.api = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self._last_battery = 100
        self._last_temp = 0.0

    def send(self, text: str, reply_markup=None):
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        try:
            requests.post(f"{self.api}/sendMessage", json=data, timeout=10)
        except Exception as e:
            print(f"[send error] {e}")

    def check_alerts(self):
        m = collector.collect()
        if 0 < m.battery_pct <= BATTERY_ALERT and m.battery_pct < self._last_battery:
            self.send(f"⚠️ *BATTERAI RENDAH*: {m.battery_pct}% ({m.battery_status})")
        self._last_battery = m.battery_pct
        if m.cpu_temp_c >= TEMP_ALERT and m.cpu_temp_c > self._last_temp:
            self.send(f"🌡️ *SUHU PANAS*: {m.cpu_temp_c}°C")
        self._last_temp = m.cpu_temp_c

    def status_text(self) -> str:
        m = collector.collect()
        return (
            f"📊 *STATUS MAC*\n"
            f"Baterai: {m.battery_pct}% ({m.battery_status})\n"
            f"Suhu CPU: {m.cpu_temp_c}°C\n"
            f"Load avg: {m.load_avg}\n"
            f"App berat: {', '.join(m.heavy_apps) or 'none'}"
        )

    def help_text(self) -> str:
        return (
            "*MacBoost Bot*\n"
            "/status - laporan baterai/suhu/beban\n"
            "/kill <app> - matikan app\n"
            "/killall - matikan app berat\n"
            "/shutdown - matikan Mac\n"
            "/restart - restart Mac\n"
            "Atau pakai tombol di bawah."
        )

    def handle_text(self, text: str):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/start", "help", "/help"):
            self.send(self.help_text(), _keyboard())
        elif cmd in ("/status", "status"):
            self.send(self.status_text(), _keyboard())
        elif cmd in ("/kill", "kill"):
            if not arg:
                self.send("Pakai: `kill <nama app>`")
            else:
                self.send("✅ " + collector.kill_app(arg))
        elif cmd in ("/killall", "killall"):
            self.send("🧹 " + collector.kill_all_heavy())
        elif cmd in ("/shutdown", "shutdown", "off"):
            self.send("🔌 Mematikan Mac...")
            collector.shutdown()
        elif cmd in ("/restart", "restart"):
            self.send("🔄 Restart Mac...")
            collector.restart()
        else:
            self.send("Perintah tidak dikenal. Ketik /help.")

    def handle_callback(self, data: str):
        if data == "status":
            self.send(self.status_text(), _keyboard())
        elif data == "killall":
            self.send("🧹 " + collector.kill_all_heavy())
        elif data == "shutdown":
            self.send("🔌 Mematikan Mac...")
            collector.shutdown()
        elif data == "restart":
            self.send("🔄 Restart Mac...")
            collector.restart()

    def poll(self):
        try:
            r = requests.get(
                f"{self.api}/getUpdates",
                params={"timeout": COMMAND_TIMEOUT, "offset": self.offset},
                timeout=COMMAND_TIMEOUT + 5,
            )
            data = r.json()
        except Exception as e:
            print(f"[poll error] {e}")
            return
        for upd in data.get("result", []):
            self.offset = upd["update_id"] + 1
            if "message" in upd:
                chat = upd["message"].get("chat", {})
                if str(chat.get("id")) == self.chat_id:
                    self.handle_text(upd["message"].get("text", ""))
            elif "callback_query" in upd:
                cb = upd["callback_query"]
                if str(cb.get("message", {}).get("chat", {}).get("id")) == self.chat_id:
                    self.handle_callback(cb.get("data", ""))
                    requests.post(
                        f"{self.api}/answerCallbackQuery",
                        json={"callback_query_id": cb["id"]},
                        timeout=10,
                    )

    def run(self):
        self.send("🤖 *MacBoost aktif.* Ketik /help atau pakai tombol.", _keyboard())
        while True:
            self.check_alerts()
            self.poll()
            time.sleep(POLL_INTERVAL)
