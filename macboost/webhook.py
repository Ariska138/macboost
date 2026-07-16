"""Webhook server for MacBoost — terima update Telegram secara realtime.

Jalankan bersama `cloudflared tunnel` agar Telegram bisa POST langsung ke bot
tanpa polling delay.
"""
from __future__ import annotations

import os
import threading

from flask import Flask, request, jsonify

from . import collector
from .bot import Bot, acquire_lock, release_lock

app = Flask(__name__)

_bot: Bot | None = None
_lock = threading.Lock()


def init_bot(token: str, chat_id: str) -> Bot:
    global _bot
    _bot = Bot(token, chat_id)
    return _bot


@app.route("/webhook", methods=["POST"])
def webhook():
    if _bot is None:
        return jsonify({"error": "bot not ready"}), 503
    try:
        update = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({"error": "bad json"}), 400
    # proses di thread terpisah agar respon HTTP cepat (realtime)
    threading.Thread(target=_bot.handle_update, args=(update,), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "bot": _bot is not None})


def run_webhook(host: str = "127.0.0.1", port: int = 8000) -> None:
    app.run(host=host, port=port, threaded=True)
