"""Telegram bot handler for MacBoost with interactive reply-keyboard menu.

Setiap klik menu meng-edit pesan terakhir (text + reply keyboard) sehingga
keyboard berubah-ubah sesuai state, dan tiap sub-menu punya tombol
🔙 Kembali ke menu utama.
"""
from __future__ import annotations

import time

import requests

from . import collector
from . import logger

POLL_INTERVAL = 5
COMMAND_TIMEOUT = 30
BATTERY_ALERT = 20
TEMP_ALERT = 80

# ----- Reply keyboard per state -----
MAIN_KEYBOARD = {
    "keyboard": [
        ["📊 Status", "ℹ️ Info Laptop"],
        ["🖥️ Monitoring App", "🧹 Kill App Berat"],
        ["🔄 Update", "⚙️ Kontrol"],
        ["📜 Logs", "❓ Help"],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

BACK_KEYBOARD = {
    "keyboard": [["🔙 Kembali"]],
    "resize_keyboard": True,
}

INFO_KEYBOARD = {
    "keyboard": [["🔄 Refresh", "🔙 Kembali"]],
    "resize_keyboard": True,
}

MONITOR_KEYBOARD = {
    "keyboard": [["🔄 Refresh", "🔙 Kembali"]],
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
        self.state = "main"  # 'main'|'info'|'monitor'|'control'
        self._last_msg_id = None  # id pesan menu terakhir yg diedit

    # ---------- send helpers ----------
    def typing(self):
        """Kirim chat action 'typing' sebagai indikator sedang memproses."""
        try:
            requests.post(
                f"{self.api}/sendChatAction",
                json={"chat_id": self.chat_id, "action": "typing"},
                timeout=10,
            )
        except Exception as e:
            logger.log(f"[typing error] {e}")

    def processing(self):
        """Edit/menu jadi pesan 'sedang memproses' + kirim indikator typing."""
        self.typing()
        self.edit_menu("⏳ *Memproses...*", None)

    def send(self, text: str, reply_markup=None, parse="Markdown"):
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse}
        if reply_markup:
            data["reply_markup"] = reply_markup
        try:
            r = requests.post(f"{self.api}/sendMessage", json=data, timeout=10)
            try:
                self._last_msg_id = r.json().get("result", {}).get("message_id")
            except Exception:
                pass
        except Exception as e:
            logger.log(f"[send error] {e}")

    def edit(self, msg_id: int, text: str, reply_markup=None):
        data = {"chat_id": self.chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        try:
            requests.post(f"{self.api}/editMessageText", json=data, timeout=10)
        except Exception as e:
            logger.log(f"[edit error] {e}")

    def edit_menu(self, text: str, reply_markup):
        """Edit pesan menu terakhir (atau kirim baru jika belum ada)."""
        if self._last_msg_id:
            self.edit(self._last_msg_id, text, reply_markup)
        else:
            self.send(text, reply_markup)

    def show_main(self, text: str = "📋 *MENU UTAMA* — pilih:"):
        self.state = "main"
        if self._last_msg_id:
            self.edit(self._last_msg_id, text, MAIN_KEYBOARD)
        else:
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

    def check_update(self):
        try:
            res = collector.check_update()
        except Exception as e:
            print(f"[update check error] {e}")
            return
        if res["behind"]:
            summary = collector.update_summary()
            self.send(
                f"📦 *UPDATE TERSEDIA*\n"
                f"{res['commits']} commit baru di remote:\n"
                f"```{summary}```\n"
                f"Jalankan `git pull` di Mac untuk update."
            )

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
            "/status /info /monitor /update /logs /kill <app> /killall /shutdown /restart"
        )

    # ---------- menu actions (edit pesan terakhir) ----------
    def act_status(self):
        self.processing()
        self.edit_menu(self.status_text(), MAIN_KEYBOARD)

    def act_info(self):
        self.processing()
        self.state = "info"
        self.edit_menu(self.info_text(), INFO_KEYBOARD)

    def act_control(self):
        self.processing()
        self.state = "control"
        self.edit_menu(
            "⚙️ *KONTROL*\nPilih aksi (hati-hati dengan shutdown/restart):",
            CONTROL_KEYBOARD,
        )

    def act_killall(self):
        self.processing()
        self.send("🧹 " + collector.kill_all_heavy())
        # tetap di menu control
        self.edit_menu(
            "⚙️ *KONTROL*\nPilih aksi (hati-hati dengan shutdown/restart):",
            CONTROL_KEYBOARD,
        )

    def act_monitor(self):
        self.processing()
        self.state = "monitor"
        self.edit_menu(collector.monitor_apps_text(), MONITOR_KEYBOARD)

    def act_update(self):
        self.processing()
        res = collector.check_update()
        if res["behind"]:
            summary = collector.update_summary()
            self.edit_menu(
                f"📦 *UPDATE TERSEDIA*\n"
                f"{res['commits']} commit baru:\n"
                f"```{summary}```",
                MAIN_KEYBOARD,
            )
        else:
            self.edit_menu(
                f"✅ *SUDAH TERBARU*\nLokal: `{res['local'][:7]}`\nRemote: `{res['remote'][:7]}`",
                MAIN_KEYBOARD,
            )

    def act_refresh(self):
        self.processing()
        if self.state == "info":
            self.edit_menu(self.info_text(), INFO_KEYBOARD)
        elif self.state == "monitor":
            self.edit_menu(collector.monitor_apps_text(), MONITOR_KEYBOARD)
        else:
            m = collector.collect()
            self.edit_menu(
                f"🔄 Refresh:\nBaterai {m.battery_pct}% | Load {m.load_avg}",
                MAIN_KEYBOARD,
            )

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
        low = t.lower()

        # back selalu prioritas
        if t == "🔙 kembali":
            logger.log("ACT: back")
            self.show_main()
            return

        if low in ("/start", "/help", "help", "❓ help"):
            self.show_main(self.help_text())
            return
        if low in ("/logs", "📜 logs"):
            logger.log("ACT: logs")
            self.send("📜 *LOGS* (maks 1000 baris):\n" + logger.log_text(), MAIN_KEYBOARD)
            return
        if low in ("/status", "📊 status"):
            logger.log("ACT: status"); self.act_status(); return
        if low in ("/info", "ℹ️ info laptop"):
            logger.log("ACT: info"); self.act_info(); return
        if low in ("/monitor", "🖥️ monitoring app"):
            logger.log("ACT: monitor"); self.act_monitor(); return
        if low in ("/update", "🔄 update"):
            logger.log("ACT: update"); self.act_update(); return
        if low in ("/killall", "🧹 kill app berat"):
            logger.log("ACT: killall"); self.act_killall(); return
        if low in ("⚙️ kontrol",):
            logger.log("ACT: control"); self.act_control(); return
        if low in ("🔄 refresh", "/refresh"):
            logger.log("ACT: refresh"); self.act_refresh(); return
        if t == "⏻ shutdown":
            logger.log("ACT: shutdown"); self.ask_shutdown(); return
        if t == "🔄 restart":
            logger.log("ACT: restart"); self.do_restart(); self.show_main(); return
        if t == "🧹 kill semua app":
            logger.log("ACT: killall"); self.act_killall(); return
        # kill <app> manual
        if low.startswith("/kill ") or t.lower().startswith("kill "):
            arg = t.split(" ", 1)[1].strip() if " " in t else ""
            if arg:
                self.send("✅ " + collector.kill_app(arg))
            else:
                self.send("Format: `kill <nama app>`")
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
        except Exception as e:
            logger.log(f"[poll error] {e}")
            return
        try:
            data = r.json()
        except Exception as e:
            logger.log(f"[poll json error] {e}")
            return
        if not data.get("ok"):
            logger.log(f"[poll not ok] {data}")
            return
        for upd in data.get("result", []):
            self.offset = upd["update_id"] + 1
            if "message" in upd:
                chat = upd["message"].get("chat", {})
                if str(chat.get("id")) == self.chat_id:
                    text = upd["message"].get("text", "")
                    logger.log(f"RCV: {text}")
                    self.typing()
                    self.handle_text(text)
            elif "callback_query" in upd:
                cb = upd["callback_query"]
                if str(cb.get("message", {}).get("chat", {}).get("id")) == self.chat_id:
                    self.typing()
                    self.handle_callback(cb.get("data", ""), cb["message"]["message_id"])
                    requests.post(
                        f"{self.api}/answerCallbackQuery",
                        json={"callback_query_id": cb["id"]},
                        timeout=10,
                    )

    def run(self):
        logger.log("BOT: started")
        self.send("🤖 *MacBoost aktif.*", MAIN_KEYBOARD)
        self.show_main()
        last_update_check = 0.0
        while True:
            self.check_alerts()
            now = time.time()
            if now - last_update_check >= 300:  # cek update tiap 5 menit
                self.check_update()
                last_update_check = now
            self.poll()
            time.sleep(POLL_INTERVAL)
