# Multi-Akun Git & SSH di Mac (ariska138 + finlup)

Panduan setup agar satu Mac bisa pakai 2 identitas GitHub berbeda otomatis
berdasarkan folder project. Terapkan di MacBook Air 2015 (user `mac`).

## 1. Kebutuhan

- `ariska138@gmail.com` → key `~/.ssh/id_ed25519` (akun GitHub `Ariska138`)
- `dev@finlup.id` → key `~/.ssh/id_ed25519_finlup` (akun GitHub `finlup`)

## 2. SSH config

Edit `~/.ssh/config`:

```
# Default ariska138
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  UseKeychain yes
  IdentitiesOnly yes

# Alias eksplisit
Host github.com-ariska
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  UseKeychain yes
  IdentitiesOnly yes

# finlup
Host github.com-finlup
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_finlup
  UseKeychain yes
  IdentitiesOnly yes
```

Verifikasi:
```bash
ssh -T git@github.com              # Hi Ariska138!
ssh -T git@github.com-finlup       # Hi finlup!
```

## 3. Git identity per folder

`~/.gitconfig` (global):
```
[user]
  email = ariska138@gmail.com
  name = Ariska Hidayat
[includeIf "gitdir:~/Projects/Ariska/"]
  path = ~/.gitconfig-ariska
[includeIf "gitdir:~/Projects/Finlup/"]
  path = ~/.gitconfig-finlup
```

`~/.gitconfig-ariska`:
```
[user]
  email = ariska138@gmail.com
  name = Ariska Hidayat
```

`~/.gitconfig-finlup`:
```
[user]
  email = dev@finlup.id
  name = finlup
```

## 4. Penggunaan

- Repo Ariska (termasuk `macboost` di `~/Projects/ThisPC`):
  commit otomatis `ariska138@gmail.com`, remote `git@github.com:Ariska138/<repo>.git`.
- Repo Finlup: letakkan di `~/Projects/Finlup/`, lalu:
  ```bash
  git remote set-url origin git@github.com-finlup:finlupid/<repo>.git
  ```
  commit otomatis `dev@finlup.id`.

## 5. Troubleshoot

- `Permission denied (publickey)` saat push → key belum di-add ke ssh-agent:
  `ssh-add ~/.ssh/id_ed25519` (masukkan passphrase). `UseKeychain yes` ingat di
  session berikutnya.
- Email commit salah → cek `git config user.email` di folder repo, pastikan path
  `includeIf` cocok dengan lokasi folder (case-sensitive, pakai `gitdir:` bukan `gitdir`).
- Jangan commit token/secret → selalu via `.env` + `.gitignore`.
