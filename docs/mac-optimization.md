# Tips Optimasi MacBook (SFA-JAGO / ThisPC)

> Dokumen living ini berisi langkah optimasi yang SUDAH dilakuin di MacBook Air 7,2
> (2015, i5 dual-core 1.8GHz, 8GB RAM, macOS 12.7.6) milik user `mac`.
> Tujuannya: jadi referensi & dasar pengembangan tool otomasi selanjutnya
> (misal monitoring Telegram di `mac-optimizer/`).

## 0. Setup SSH & Git Identity (multi-akun)

Mac ini punya 2 identitas GitHub: `ariska138@gmail.com` (default) & `dev@finlup.id`.
Konfigurasi sudah di-setup agar otomatis benar per folder.

### 0.1 `~/.ssh/config` (pilih key per host)
```
# Default -> ariska138@gmail.com
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  UseKeychain yes
  IdentitiesOnly yes

# Alias eksplisit ariska
Host github.com-ariska
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  UseKeychain yes
  IdentitiesOnly yes

# dev@finlup.id
Host github.com-finlup
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_finlup
  UseKeychain yes
  IdentitiesOnly yes
```
- `UseKeychain yes` → passphrase diingat, tidak minta tiap push.
- Untuk repo finlup, remote pakai alias: `git@github.com-finlup:finlupid/<repo>.git`.

### 0.2 Git per-folder identity (`~/.gitconfig` + includeIf)
Global default = `ariska138@gmail.com`. Tambahan di `~/.gitconfig`:
```
[includeIf "gitdir:~/Projects/Ariska/"]
  path = ~/.gitconfig-ariska
[includeIf "gitdir:~/Projects/Finlup/"]
  path = ~/.gitconfig-finlup
```
- `~/.gitconfig-ariska` → `ariska138@gmail.com` / `Ariska Hidayat`
- `~/.gitconfig-finlup` → `dev@finlup.id` / `finlup`
- Efek: folder `~/Projects/Finlup/**` otomatis commit pakai email finlup.

### 0.3 Catatan keamanan
- **JANGAN** kirim Telegram Bot Token ke chat LLM (pernah ke-expose, harus di-revoke
  via @BotFather). Simpan di `.env` (gitignored), bukan di-commit.
- Private key tetap lokal; hanya public key yang didaftarkan ke GitHub.

## 1. Profil Hardware & Constraint

- Model: MacBookAir7,2 — Intel Core i5 dual-core 1.8GHz, 2 core (HT).
- RAM: 8GB (solderan, TIDAK bisa upgrade).
- OS: macOS 12.7.6 — **TIDAK bisa upgrade ke 13+** (constraint permanen, lihat AGENTS.md global).
- Baterai: cycle 915, status **"Service Recommended"** (kapasitas turun, rawan throttling).
- Disk: 113GB SSD, setelah optimasi ~21GB free (41%).

## 2. Diagnosa Awal (kenapa lemot/hank)

- RAM 8GB penuh → swap ke disk parah (pageouts > 1.2 juta, swapins 49jt+).
- Beberapa background server jalan terus walau nggak dipakai (PostgreSQL, Redis, Docker, Foxit, Zoom).
- OpenCode + Brave + WhatsApp barengan di dual-core = load avg sempat 397.
- Cache user `~/Library/Caches` menumpuk **9.7 GB** (Brave, Homebrew, pnpm, Playwright, Yarn, Claude, Antigravity, Postman).
- Uptime lama tanpa restart → swap numpuk.

## 3. Optimasi yang SUDAH DILAKUIN

### 3.1 Matiin / Uninstall Background Berat
- PostgreSQL@14: `brew services stop` + `brew uninstall` + hapus LaunchAgent auto-start.
- Redis: `brew services stop` + `brew uninstall`.
- Docker: app emang nggak terinstall; hapus 2 daemon
  (`/Library/LaunchDaemons/com.docker.socket.plist`, `com.docker.vmnetd.plist`)
  + sisa data `~/.docker`, `~/Library/Application Support/Docker Desktop`.
- Foxit PDF Reader update daemon: `sudo launchctl unload -w` + `sudo rm`.
- Zoom daemon (`us.zoom.ZoomDaemon` + updater): `sudo launchctl unload -w` + `sudo rm`.
- Kiro CLI: kill process idle (`kiro_cli_deskto`), tidak ada LaunchAgent → tidak auto-restart.

### 3.2 Bersihin Cache (~8.5 GB dibebaskan)
Dihapus: `~/Library/Caches/{pnpm, Yarn, Homebrew, ms-playwright,
com.anthropic.claudefordesktop.ShipIt, antigravity-updater,
com.postmanlabs.agent.mac.ShipIt, BraveSoftware/Brave-Browser/{Cache,Code Cache,GPUCache}}`.
Hasil: cache 9.7GB → 3.9GB, disk free 15GB → 21GB.

### 3.3 Setting Tampilan (kurangi beban GPU/WindowServer)
- Reduce Motion: `defaults write com.apple.Accessibility reduceMotionEnabled -bool true`
- Reduce Transparency: `defaults write com.apple.Accessibility reduceTransparencyEnabled -bool true`
- (efek penuh setelah logout/restart atau `killall Dock`)

### 3.4 Yang SENGAJA dibiarin (ringan & berguna)
- Alfred 5 (login item, ~MB RAM) — biarkan.
- Lightshot Screenshot (login item) — biarkan; pastikan izin Screen Recording ON
  biar shortcut langsung jalan tanpa buka app dulu.

## 4. Solusi Tanpa Biaya untuk Baterai Rusak

Karena ganti baterai butuh biaya, pakai mitigasi software/kebiasaan:
1. **Selalu colok charger saat pakai berat** (OpenCode/Brave banyak tab) → cegah throttling.
2. Reduce Motion/Transparency (sudah ON).
3. Jaga suhu (pakai stand/laptop diangkat) → cegah throttling panas.
4. Restart rutin (seminggu sekali) → swap bersih.
5. Low Power Mode (`pmset lowpowermode`) **TIDAK didukung** di Mac 2015 + macOS 12 → skip.

## 5. Tool Otomasi: mac-optimizer/

Script `mac-telegram-monitor.sh` + LaunchAgent `com.user.mactmon.plist`:
- Kirim alert ke Telegram kalau baterai <20% atau suhu >80°C.
- Terima perintah dari Telegram: `status`, `kill <app>`, `killall`,
  `shutdown`/`off`, `restart`, `help`.
- Cara pakai:
  1. Isi `BOT_TOKEN` & `CHAT_ID` di script (dapat dari @BotFather + getUpdates).
  2. `chmod +x mac-telegram-monitor.sh`
  3. `cp com.user.mactmon.plist ~/Library/LaunchAgents/`
  4. `launchctl load ~/Library/LaunchAgents/com.user.mactmon.plist`
- Catatan: `powermetrics` & `shutdown` butuh sudo → jalankan sebagai user yang punya
  akses, atau tambahkan exception sudoers untuk script ini.

## 6. Rekomendasi Pengembangan Lanjut

- [ ] Tambah notif "load avg tinggi" (misal >10) ke Telegram.
- [ ] Auto-kill app berat otomatis kalau baterai <15% & tidak dicolok.
- [ ] Log historis baterai/suhu ke file CSV untuk analisa.
- [ ] Web dashboard lokal (Python http.server) sebagai alternatif Telegram.
- [ ] Deteksi app baru yang nambah diri ke login items (alert perubahan).
- [ ] Integrasi dengan AGENTS.md global: constraint macOS 12.7.6 (tidak bisa
      upgrade, deploy Cloudflare lewat GitHub Actions bukan local).

## 7. Catatan Penting

- Jangan pernah upgrade macOS ke 13+ (hardware limit + butuh workerd untuk
  `@opennextjs/cloudflare deploy` yang gagal di 12.7.6).
- Deploy Cloudflare Workers tetap lewat GitHub Actions (Ubuntu), bukan local.
- Semua perintah `sudo` di atas dijalankan manual oleh user (agent tidak bisa
  input password).
