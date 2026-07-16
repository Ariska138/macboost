"""Telegram bot handler for MacBoost with interactive menu."""
from __future__ import annotations

import time

import requests

from . import collector

POLL_INTERVAL = 5
COMMAND_TIMEOUT = 30
BATTERY_ALERT = 20
TEMP_ALERT = 80

# ----- Reply keyboard (menu navigasi persisten) -----
MAIN_KEYBOARD = {
    "keyboard": [
        ["📊 Status", "ℹ️ Info Laptop"],
        ["🖥️ Monitoring App", "🧹 Kill App Berat"],
        ["⚙️ Kontrol", "❓ Help"],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

BACK_KEYBOARD = {
    "keyboard": [["🔙 Kembali"]],
    "resize_keyboard": True,
}

CONTROL_KEYBOARD = {
    "keyboard": [
        ["⏻ Shutdown", "🔄 Restart"],
        ["🧹 Kill Semua App", "🔙 Kembali"],
    ],
    "resize_keyboard": True,
}

# Inline keyboard untuk konfirmasi aksi berisiko
CONFIRM_KB = {
    "inline_keyboard": [
        [
            {"text": "✅ Ya", "callback_data": "confirm_shutdown"},
            {"text": "❌ Batal", "callback_data": "cancel"},
        ]
    ]
}


class Bot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = str(chat_id)
        self.api = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self._last_battery = 100
        self._last_temp = 0.0
        self.state = {}  # chat_id -> 'main'|'control'|'info'

    # ---------- send helpers ----------
    def send(self, text: str, reply_markup=None, parse="Markdown"):
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse}
        if reply_markup:
            data["reply_markup"] = reply_markup
        try:
            requests.post(f"{self.api}/sendMessage", json=data, timeout=10)
        except Exception as e:
            print(f"[send error] {e}")

    def edit(self, msg_id: int, text: str, reply_markup=None):
        data = {"chat_id": self.chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        try:
            requests.post(f"{self.api}/editMessageText", json=data, timeout=10)
        except Exception as e:
            print(f"[edit error] {e}")

    def show_main(self, text: str = "📋 *MENU UTAMA* — pilih:"):
        self.state[self.chat_id] = "main"
        self.send(text, MAIN_KEYBOARD)

    # ---------- alerts ----------
    def check_alerts(self):
        m = collector.collect()
        if 0 < m.battery_pct <= BATTERY_ALERT and m.battery_pct < self._last_battery:
            self.send(f"⚠️ *BATTERAI RENDAH*: {m.battery_pct}% ({m.battery_status})")
        self._last_battery = m.battery_pct
        if m.cpu_temp_c >= TEMP_ALERT and m.cpu_temp_c > self._last_temp:
            self.send(f"🌡️ *SUHU PANAS*: {m.cpu_temp_c}°C")
        self._last_temp = m.cpu_temp_c

    # ---------- text builders ----------
    def status_text(self) -> str:
        m = collector.collect()
        return (
            f"📊 *STATUS MAC*\n"
            f"Baterai: {m.battery_pct}% ({m.battery_status})\n"
            f"Suhu CPU: {m.cpu_temp_c}°C\n"
            f"Load avg: {m.load_avg}\n"
            f"App berat: {', '.join(m.heavy_apps) or 'none'}"
        )

    def info_text(self) -> str:
        d = collector.collect_full()
        apps = ", ".join(d["running_apps"][:15]) or "none"
        if len(d["running_apps"]) > 15:
            apps += f" …(+{len(d['running_apps'])-15})"
        svcs = ", ".join((s.split(".")[-2] if "." in s else s)
                         for s in d["running_services"][:12]) or "none"
        if len(d["running_services"]) > 12:
            svcs += f" …(+{len(d['running_services'])-12})"
        storage = "\n    • " + "\n    • ".join(d["storage"])
        net = d["network"]
        return (
            f"ℹ️ *INFO LAPTOP*\n\n"
            f"💻 CPU: {d['cpu']}\n"
            f"🔋 Baterai: {d['battery_pct']}% ({d['battery_status']})\n"
            f"   Cycle: {d['battery_cycle']} | Condition: {d['battery_condition']}\n"
            f"🌡️ Suhu CPU: {d['cpu_temp_c']}°C\n"
            f"📈 Load avg: {d['load_avg']}\n"
            f"🧠 RAM: {d['ram']}\n"
            f"💾 Storage:{storage}\n"
            f"🌐 Network:\n"
            f"   Interface: {net['interface']}\n"
            f"   IP lokal: {net['local']}\n"
            f"   IP publik: {net['public']}\n"
            f"📱 App jalan ({len(d['running_apps'])}): {apps}\n"
            f"⚙️ Service ({len(d['running_services'])}): {svcs}"
        )

    def help_text(self) -> str:
        return (
            "*MacBoost Bot*\n"
            "Gunakan tombol menu di bawah untuk navigasi.\n"
            "Perintah cepat:\n"
            "/status /info /monitor /kill <app> /killall /shutdown /restart"
        )

    # ---------- menu actions ----------
    def act_status(self):
        self.send(self.status_text(), MAIN_KEYBOARD)

    def act_info(self):
        self.state[self.chat_id] = "info"
        self.send(self.info_text(), BACK_KEYBOARD)

    def act_control(self):
        self.state[self.chat_id] = "control"
        self.send(
            "⚙️ *KONTROL*\nPilih aksi (hati-hati dengan shutdown/restart):",
            CONTROL_KEYBOARD,
        )

    def act_killall(self):
        self.send("🧹 " + collector.kill_all_heavy(), MAIN_KEYBOARD)

    def act_monitor(self):
        self.state[self.chat_id] = "monitor"
        self.send(collector.monitor_apps_text(), BACK_KEYBOARD)

    def ask_shutdown(self):
        self.send("⏻ *Yakin matikan Mac?*", CONFIRM_KB)

    def do_shutdown(self):
        self.send("🔌 Mematikan Mac...")
        collector.shutdown()

    def do_restart(self):
        self.send("🔄 Restart Mac...")
        collector.restart()

    # ---------- text router ----------
    def handle_text(self, text: str):
        t = text.strip()
        # perintah slash tetap didukung
        low = t.lower()
        if low in ("/start", "/help", "help", "❓ help"):
            self.show_main(self.help_text())
            return
        if low in ("/status", "📊 status"):
            self.act_status(); return
        if low in ("/info", "ℹ️ info laptop"):
            self.act_info(); return
        if low in ("/monitor", "🖥️ monitoring app"):
            self.act_monitor(); return
        if low in ("/killall", "🧹 kill app berat"):
            self.act_killall(); return
        if low in ("⚙️ kontrol",):
            self.act_control(); return
        if low in ("🔄 refresh", "/refresh"):
            m = collector.collect()
            self.send(f"🔄 Refresh:\nBaterai {m.battery_pct}% | Load {m.load_avg}", MAIN_KEYBOARD)
            return
        if t == "🔙 kembali":
            self.show_main(); return
        if t == "⏻ shutdown":
            self.ask_shutdown(); return
        if t == "🔄 restart":
            self.do_restart(); self.show_main(); return
        if t == "🧹 kill semua app":
            self.act_killall(); self.act_control(); return
        # kill <app> manual
        if low.startswith("/kill ") or t.lower().startswith("kill "):
            arg = t.split(" ", 1)[1].strip() if " " in t else ""
            if arg:
                self.send("✅ " + collector.kill_app(arg), MAIN_KEYBOARD)
            else:
                self.send("Format: `kill <nama app>`", MAIN_KEYBOARD)
            return
        # default
        self.send("Perintah tidak dikenal. Pakai tombol menu atau /help.", MAIN_KEYBOARD)

    # ---------- callback (inline) ----------
    def handle_callback(self, data: str, msg_id: int):
        if data == "confirm_shutdown":
            self.do_shutdown()
        elif data == "cancel":
            self.edit(msg_id, "❌ Dibatalkan.", MAIN_KEYBOARD)
        elif data == "status":
            self.edit(msg_id, self.status_text())
        elif data == "info":
            self.edit(msg_id, self.info_text())

    # ---------- poll ----------
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
                    self.handle_callback(cb.get("data", ""), cb["message"]["message_id"])
                    requests.post(
                        f"{self.api}/answerCallbackQuery",
                        json={"callback_query_id": cb["id"]},
                        timeout=10,
                    )

    def run(self):
        self.send("🤖 *MacBoost aktif.*", MAIN_KEYBOARD)
        self.show_main()
        while True:
            self.check_alerts()
            self.poll()
            time.sleep(POLL_INTERVAL)
