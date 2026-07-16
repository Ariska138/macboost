# Docs Index — Mac Optimizer (macboost)

Ringkasan dokumentasi repo ini.

## Daftar Docs

- [mac-optimization.md](mac-optimization.md) — tips optimasi Mac lawas
  (macOS 12.7.6, baterai rusak): matiin background server, bersih cache,
  setting tampilan, tool monitoring Telegram, roadmap pengembangan.
- [git-identity.md](git-identity.md) — setup multi-akun Git/SSH
  (ariska138 + finlup) otomatis per folder via `~/.ssh/config` + `includeIf`.
- [logging.md](logging.md) — log berputar (maks 1000 baris) +
  perintah `/logs` di Telegram untuk debug saat bot tidak respon.

## Quick Reference

| Topik | Lokasi |
|-------|--------|
| Profil hardware & constraint | mac-optimization.md §1 |
| Optimasi dilakukan | mac-optimization.md §3 |
| Solusi baterai tanpa biaya | mac-optimization.md §4 |
| Tool Telegram monitor | mac-optimization.md §5 + `mac-optimizer/` |
| Keamanan token | mac-optimization.md §0.3 |
| SSH multi-akun | git-identity.md §2 |
| Git identity per folder | git-identity.md §3 |

## Setup Cepat (recap)

1. Bot Telegram: isi `MACTMON_BOT_TOKEN`/`MACTMON_CHAT_ID` di `.env` (gitignored).
2. `chmod +x mac-optimizer/mac-telegram-monitor.py`
3. `cp mac-optimizer/com.user.mactmon.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.user.mactmon.plist`
4. Sudoers: `mac ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/powermetrics`
