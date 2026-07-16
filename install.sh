#!/usr/bin/env bash
#
# install.sh - installer MacBoost (macOS)
# Menyiapkan: virtualenv, dependency, sudoers, LaunchAgent.
#
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_LABEL="com.user.macboost"
AGENT_PLIST="$HOME/Library/LaunchAgents/${AGENT_LABEL}.plist"
VENV="$REPO_DIR/.venv"

echo "== MacBoost installer =="

# 1. virtualenv
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet -r "$REPO_DIR/requirements.txt"

# 2. .env
if [ ! -f "$REPO_DIR/.env" ]; then
  cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
  echo "!! Isi $REPO_DIR/.env dengan MACTMON_BOT_TOKEN & MACTMON_CHAT_ID"
fi

# 3. sudoers (shutdown + powermetrics tanpa password)
SUDOERS=/etc/sudoers.d/macboost
if [ ! -f "$SUDOERS" ]; then
  echo "== Menambahkan sudoers (perlu password sudo) =="
  echo "$USER ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/powermetrics" | \
    sudo tee "$SUDOERS" >/dev/null
  sudo chmod 440 "$SUDOERS"
  sudo visudo -c
fi

# 4. LaunchAgent
cat > "$AGENT_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV}/bin/python</string>
        <string>-m</string>
        <string>macboost.cli</string>
        <string>bot</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
    <key>StandardOutPath</key>
    <string>${REPO_DIR}/macboost.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_DIR}/macboost.err</string>
</dict>
</plist>
EOF

launchctl load "$AGENT_PLIST" 2>/dev/null || true
echo "== Selesai. Bot jalan sebagai LaunchAgent. Cek log: $REPO_DIR/macboost.log =="
