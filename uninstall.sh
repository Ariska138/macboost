#!/usr/bin/env bash
# uninstall.sh - hentikan MacBoost LaunchAgent
set -e
AGENT_LABEL="com.user.macboost"
AGENT_PLIST="$HOME/Library/LaunchAgents/${AGENT_LABEL}.plist"
launchctl unload "$AGENT_PLIST" 2>/dev/null || true
rm -f "$AGENT_PLIST"
echo "MacBoost di-unload. (file repo & .venv tidak dihapus)"
