#!/usr/bin/env bash
#
# tunnel-named.sh - jalankan MacBoost bot realtime via Cloudflare NAMED tunnel
# (URL stabil, tidak berubah tiap restart). Token dibaca dari .env (gitignored),
# TIDAK di-hardcode ke repo.
#
set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"
source "$REPO_DIR/.venv/bin/activate"

# ambil env cloudflare (token & account) dari .env tanpa print ke log
set -a
source "$REPO_DIR/.env"
set +a

PORT="${MACBOOST_WEBHOOK_PORT:-8000}"
TUNNEL_NAME="${MACBOOST_TUNNEL_NAME:-macboost}"
TUNNEL_HOST="${MACBOOST_TUNNEL_HOST:-macboost.local.finlup.id}"

# jalankan tunnel permanen (DNS CNAME sudah diarahkan ke tunnel ini)
cloudflared tunnel run --url "http://localhost:${PORT}" "$TUNNEL_NAME" &
TUNNEL_PID=$!

# tunggu tunnel siap, lalu set webhook
PUBLIC_URL="https://${TUNNEL_HOST}"
echo "== Named tunnel: $TUNNEL_NAME =="
echo "== Public URL: $PUBLIC_URL =="
export MACBOOST_PUBLIC_URL="$PUBLIC_URL"

# beri waktu tunnel connect sebelum setWebhook
sleep 8

# jalankan bot webhook (setWebhook otomatis via MACBOOST_PUBLIC_URL)
python -m macboost.cli webhook &
BOT_PID=$!

wait
