"""Local web dashboard for MacBoost."""
from __future__ import annotations

from flask import Flask, jsonify

from . import collector

app = Flask(__name__)


@app.route("/")
def index():
    return """
    <!doctype html><html><head><meta charset="utf-8">
    <title>MacBoost</title>
    <style>body{font-family:monospace;background:#111;color:#0f0;padding:2rem}
    button{margin:.3rem;padding:.5rem 1rem;cursor:pointer}</style>
    </head><body>
    <h1>🖥️ MacBoost Dashboard</h1>
    <pre id="status">loading...</pre>
    <button onclick="act('killall')">🧹 Kill All</button>
    <button onclick="act('shutdown')">⏻ Shutdown</button>
    <button onclick="act('restart')">🔄 Restart</button>
    <script>
    async function load(){
      const r=await fetch('/api/status');const d=await r.json();
      document.getElementById('status').textContent=JSON.stringify(d,null,2);
    }
    async function act(a){await fetch('/api/'+a,{method:'POST'});load();}
    load();setInterval(load,10000);
    </script></body></html>
    """


@app.route("/api/status")
def api_status():
    m = collector.collect()
    return jsonify({
        "battery_pct": m.battery_pct,
        "battery_status": m.battery_status,
        "cpu_temp_c": m.cpu_temp_c,
        "load_avg": m.load_avg,
        "heavy_apps": m.heavy_apps,
    })


@app.route("/api/killall", methods=["POST"])
def api_killall():
    return jsonify({"result": collector.kill_all_heavy()})


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    collector.shutdown()
    return jsonify({"result": "shutting down"})


@app.route("/api/restart", methods=["POST"])
def api_restart():
    collector.restart()
    return jsonify({"result": "restarting"})


def run_dashboard(host="127.0.0.1", port=8080):
    app.run(host=host, port=port)
