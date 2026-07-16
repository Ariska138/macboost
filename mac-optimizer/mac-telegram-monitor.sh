#!/usr/bin/env bash
#
# mac-telegram-monitor.sh
# Monitoring & kontrol MacBook via Telegram.
# Fitur: alert baterai/suhu, matikan app remote, shutdown/restart.
#
# SETUP:
#   1. Isi BOT_TOKEN dan CHAT_ID di bawah.
#   2. chmod +x mac-telegram-monitor.sh
#   3. Jalankan via LaunchAgent (lihat com.user.mactmon.plist).
#
# Perintah dari Telegram (kirim sebagai pesan ke bot):
#   status          -> laporan baterai/suhu/beban
#   kill <app>      -> quit app (misal: kill OpenCode)
#   killall         -> quit app berat (OpenCode, Brave, WhatsApp)
#   shutdown        -> matikan Mac
#   restart         -> restart Mac
#   off             -> matikan Mac (alias shutdown)
#
# Keamanan: hanya CHAT_ID di atas yang direspon bot.

BOT_TOKEN="ISI_BOT_TOKEN_DISINI"
CHAT_ID="ISI_CHAT_ID_DISINI"

# App yang dianggap "berat" untuk perintah killall
HEAVY_APPS=("OpenCode" "Brave Browser" "WhatsApp")

# Ambang batas alert
BATTERY_ALERT_THRESHOLD=20   # % baterai di bawah ini -> alert
TEMP_ALERT_THRESHOLD=80      # derajat C di atas ini -> alert

LAST_BATTERY_ALERT=100
LAST_TEMP_ALERT=0

send_msg() {
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=$1" >/dev/null 2>&1
}

get_battery() {
  # % baterai + status (charging/AC/discharging)
  pmset -g batt | awk -F';' '/Internal/{
    gsub(/[ \t]+/,"",$1); pct=$1;
    status=$3; gsub(/^[ \t]+/,"",status);
    print pct"|"status
  }'
}

get_temp() {
  # Suhu CPU (C) via powermetrics — butuh sudo; fallback pakai thermal level
  local t
  t=$(sudo powermetrics -n 1 -s cpu_power 2>/dev/null | awk -F': ' '/CPU die temperature/{print $2}' | tr -d ' C')
  if [ -z "$t" ]; then
    # fallback: baca thermal pressure dari oslog tidak reliable; pakai 0
    t=0
  fi
  echo "$t"
}

get_load() {
  uptime | awk -F'load averages:' '{print $2}' | awk '{print $1}'
}

app_running() {
  pgrep -f "$1" >/dev/null 2>&1
}

kill_app() {
  local name="$1"
  # cari process by app name (bundle)
  local pids
  pids=$(pgrep -f "$name" 2>/dev/null)
  if [ -z "$pids" ]; then
    echo "App '$name' tidak jalan."
    return
  fi
  # coba quit graceful dulu
  osascript -e "quit app \"$name\"" >/dev/null 2>&1
  sleep 2
  # force kill sisa
  pkill -f "$name" 2>/dev/null
  echo "App '$name' dimatikan."
}

handle_command() {
  local text="$1"
  local cmd
  cmd=$(echo "$text" | awk '{print $1}')
  local arg
  arg=$(echo "$text" | cut -d' ' -f2-)

  case "$cmd" in
    status)
      local b; b=$(get_battery)
      local t; t=$(get_temp)
      local l; l=$(get_load)
      send_msg "📊 STATUS MAC
Baterai: ${b}
Suhu CPU: ${t}°C
Load avg: ${l}"
      ;;
    kill)
      if [ -z "$arg" ]; then
        send_msg "Pakai: kill <nama app> (misal: kill OpenCode)"
      else
        local r; r=$(kill_app "$arg")
        send_msg "✅ $r"
      fi
      ;;
    killall)
      local msg=""
      for a in "${HEAVY_APPS[@]}"; do
        if app_running "$a"; then
          msg="${msg}
$(kill_app "$a")"
        fi
      done
      send_msg "🧹 Killall app berat:${msg}"
      ;;
    shutdown|off)
      send_msg "🔌 Mematikan Mac..."
      sudo shutdown -h now
      ;;
    restart)
      send_msg "🔄 Restart Mac..."
      sudo shutdown -r now
      ;;
    help|*)
      send_msg "Perintah:
status - laporan
kill <app> - matikan app
killall - matikan app berat
shutdown/off - matikan Mac
restart - restart Mac"
      ;;
  esac
}

poll_commands() {
  # Ambil update terbaru, hanya dari CHAT_ID, balas perintah
  local updates
  updates=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?timeout=30&offset=${1:-0}" 2>/dev/null)
  # parse sederhana: ambil chat_id + text + update_id
  echo "$updates"
}

main_loop() {
  local offset=0
  send_msg "🤖 Mac Monitor aktif. Kirim 'help' untuk daftar perintah."

  while true; do
    # --- ALERT OTOMATIS ---
    local b; b=$(get_battery)
    local pct; pct=$(echo "$b" | cut -d'|' -f1 | tr -d '%')
    local t; t=$(get_temp)

    if [ -n "$pct" ] && [ "$pct" -le "$BATTERY_ALERT_THRESHOLD" ] && [ "$pct" -lt "$LAST_BATTERY_ALERT" ]; then
      send_msg "⚠️ BATTERAI RENDAH: ${pct}% (${b#*|})"
    fi
    LAST_BATTERY_ALERT=$pct

    if [ -n "$t" ] && [ "$t" -ge "$TEMP_ALERT_THRESHOLD" ] && [ "$t" -gt "$LAST_TEMP_ALERT" ]; then
      send_msg "🌡️ SUHU PANAS: ${t}°C"
    fi
    LAST_TEMP_ALERT=$t

    # --- POLL PERINTAH ---
    local resp
    resp=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?timeout=20&offset=${offset}" 2>/dev/null)
    # Ekstrak tiap update: update_id, chat_id, text
    echo "$resp" | grep -o '"update_id":[0-9]*' | while read -r line; do
      local uid; uid=$(echo "$line" | cut -d: -f2)
      local ch; ch=$(echo "$resp" | grep -o '"chat":{"id":[0-9]*' | head -1 | grep -o '[0-9]*$')
      local tx; tx=$(echo "$resp" | grep -o '"text":"[^"]*"' | head -1 | sed 's/"text":"//;s/"$//')
      if [ "$ch" = "$CHAT_ID" ] && [ -n "$tx" ]; then
        handle_command "$tx"
      fi
      offset=$((uid + 1))
    done

    sleep 30
  done
}

main_loop
