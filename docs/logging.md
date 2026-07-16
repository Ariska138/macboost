# Logging & Debug — MacBoost

Catat aktivitas bot + error ke file log berputar (rotating) agar mudah debug
saat bot tidak merespons.

## Lokasi

- File: `macboost.log` (di root repo, sebelah `install.sh`)
- Modul: `macboost/logger.py`
- Maksimal **1000 baris** — saat melebihi, baris terlama otomatis dibuang
  (keep last 1000).

## Cara kerja

`logger.log(msg)` menulis 1 baris (newline di-strip). Saat file > 1000 baris,
hanya 1000 terakhir yang disimpan. `logger.read_logs()` /
`logger.log_text()` membaca isi untuk ditampilkan ke Telegram.

## Lihat log dari Telegram

- Tombol **📜 Logs** di menu utama, atau perintah `/logs`
- Menampilkan seluruh isi log (maks 1000 baris) dalam blok kode Markdown.
- Format: ```\n<baris log>\n```

## Yang dicatat

- Setiap pesan masuk (`handle_text`): `RCV: <teks>`
- Setiap aksi menu: `ACT: <nama>`
- Error kirim/edit: `[send error] <err>`, `[edit error] <err>`
- Error poll: `[poll error] <err>`
- Error cek update: `[update check error] <err>`
- Startup: `BOT: started`

## Tips debug saat "bot tidak respon"

1. Cek `macboost.log` via `/logs` di Telegram.
2. Pastikan hanya **SATU** instance bot jalan (LaunchAgent + manual tidak
   boleh bareng — keduanya poll `getUpdates` & saling tabrak offset).
3. Cek proses: `launchctl list | grep macboost`
4. Cek token `.env`: `MACTMON_BOT_TOKEN` & `MACTMON_CHAT_ID` terisi.
5. Restart: `launchctl kickstart -k gui/$(id -u)/com.user.macboost`
