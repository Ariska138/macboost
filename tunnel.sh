#!/usr/bin/env bash
#
# tunnel.sh - jalankan MacBoost bot dalam mode webhook (realtime)
# via Cloudflare Tunnel. Telegram POST langsung ke bot -> respon instan.
#
set -e
REPO_DIR="$(cd "$(dirname "$0") && pwd)"
cd "$REPO_DIR"
source "$REPO_DIR/.venv/bin/activate"

PORT="${MACBOOST_WEBHOOK_PORT:-8000}"
MODE="${1:-quick}"

if [ "$MODE" = "quick" ]; then
  echo "== Cloudflare Tunnel (quick, random URL) =="
  # cloudflared kasih URL publik random, kita ambil lalu set webhook
  cloudflared tunnel --url "http://localhost:${PORT}" --no-autoupdate 2>&1 | \
  while IFS= read -r line; do
    echo "$line"
    if [[ "$line" =~ https://([a-z0-9-]+\.trycloudflare\.com) ]]; then
      URL="https://${BASH_REMATCH[1]}"
      echo "== Tunnel URL: $URL =="
      export MACBOOST_PUBLIC_URL="$URL"
      # jalankan bot webhook (setWebhook otomatis via env)
      python -m macboost.cli webhook &
      break
    fi
  done
else
  echo "Usage: ./tunnel.sh quick"
fi
