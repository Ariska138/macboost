# MacBoost 🖥️⚡

Optimize & monitor **old MacBooks** (terutama macOS 12.7.6 / MacBook Air 2015)
lewat **Telegram bot** + **local web dashboard**.

Fitur:
- 📊 Monitor baterai, suhu CPU, load average, & app berat yang jalan
- ⚠️ Alert otomatis ke Telegram kalau baterai <20% atau suhu >80°C
- 🎛️ Kontrol remote: `kill <app>`, `killall`, `shutdown`, `restart`
- 🌐 Web dashboard lokal (`http://127.0.0.1:8080`)
- 🔒 Multi-user auth: hanya chat ID pemilik yang direspon

## Instalasi (macOS)

```bash
git clone git@github.com:Ariska138/macboost.git
cd macboost
chmod +x install.sh uninstall.sh
./install.sh
```

`install.sh` akan:
1. Buat virtualenv & install dependency (`requests`, `flask`, `python-dotenv`)
2. Salin `.env.example` → `.env` (isi token kamu)
3. Tambah sudoers agar `shutdown` & `powermetrics` jalan tanpa password
4. Pasang LaunchAgent agar bot jalan otomatis tiap login

## Setup Token Telegram

1. Chat `@BotFather` → `/newbot` → dapatkan **BOT_TOKEN**
2. Chat bot baru kamu → klik **Start**
3. Buka: `https://api.telegram.org/bot<TOKEN>/getUpdates` → cari `"chat":{"id":...}` = **CHAT_ID**
4. Isi di `.env`:
   ```
   MACTMON_BOT_TOKEN=xxx
   MACTMON_CHAT_ID=123456789
   ```

⚠️ **JANGAN** commit `.env` (sudah di-.gitignore). Token ter-expose = revoke di BotFather.

## Penggunaan

Perintah di Telegram:
- `/status` — laporan lengkap
- `/info` — info detail laptop: CPU, baterai (cycle/condition), suhu, RAM, storage, network (IP lokal/publik), app jalan, service/daemon
- `/monitor` — monitoring aplikasi OpenCode, Brave Browser, & Zed (status ON/OFF, PID, CPU/RAM, info SQLite DB)
- `/kill <app>` — matikan app (misal `/kill OpenCode`)
- `/killall` — matikan app berat (OpenCode, Brave, WhatsApp)
- `/shutdown` — matikan Mac
- `/restart` — restart Mac
- Tombol inline juga tersedia

Atau jalankan manual:
```bash
source .venv/bin/activate
python -m macboost.cli bot     # jalankan bot
python -m macboost.cli web     # jalankan web dashboard
python -m macboost.cli status  # cek status sekali
```

## Struktur

```
macboost/
  collector.py   # ambil metrik macOS + kill/shutdown + monitoring app/SQLite
  bot.py         # handler Telegram (poll + inline keyboard + menu monitoring)
  web.py         # Flask dashboard lokal
  cli.py         # entrypoint
docs/            # tips optimasi & setup multi-akun Git
install.sh       # installer + LaunchAgent + sudoers
uninstall.sh
```

## Monitoring Aplikasi (OpenCode / Brave / Zed)

Menu **🖥️ Monitoring App** (atau `/monitor`) menampilkan:
- Status ON/OFF + PID tiap app
- Penggunaan CPU & RAM (via `ps`)
- Info SQLite DB tiap app: ukuran file + jumlah tabel (jika `sqlite3` tersedia)

Lokasi DB yang dicek:
- **OpenCode**: `~/.config/opencode/opencode.db`
- **Brave Browser**: `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History`
- **Zed**: `~/.config/zed/zed.db`

Untuk info tabel SQLite, pastikan `sqlite3` CLI terinstall (`brew install sqlite`).

## Lisensi

MIT © Ariska Hidayat
