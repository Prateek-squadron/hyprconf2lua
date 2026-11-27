# Maintaining the AUR Package

The `PKGBUILD` and `.SRCINFO` in this directory are the canonical source for the [`hyprconf2lua`](https://aur.archlinux.org/packages/hyprconf2lua) Arch User Repository (AUR) package.

---

## 1. Prerequisites (First-time AUR Setup)

1. **Create an AUR account**:
   Register at [aur.archlinux.org/register](https://aur.archlinux.org/register).

2. **Add your SSH Public Key**:
   Go to [aur.archlinux.org/account](https://aur.archlinux.org/account) and paste your SSH public key (`cat ~/.ssh/id_ed25519.pub`).

3. **Verify SSH connection**:
   ```bash
   ssh -T aur@aur.archlinux.org
   ```
   You should see: `Interactive shell is disabled. Welcome to AUR, <username>!`

---

## 2. Publishing to AUR (Initial Import)

1. **Clone the empty AUR repository**:
   ```bash
   git clone ssh://aur@aur.archlinux.org/hyprconf2lua.git /tmp/aur-hyprconf2lua
   ```

2. **Copy the packaging files**:
   ```bash
   cp packaging/aur/PKGBUILD packaging/aur/.SRCINFO /tmp/aur-hyprconf2lua/
   ```

3. **Commit and push**:
   ```bash
   cd /tmp/aur-hyprconf2lua
   git add PKGBUILD .SRCINFO
   git commit -m "feat: initial import v1.9.0"
   git push origin master
   ```

---

## 3. Maintenance on Each New Release

Whenever a new version of `hyprconf2lua` is released and tagged on GitHub:

1. **Bump the version in `PKGBUILD`**:
   Update `pkgver=X.Y.Z` and reset `pkgrel=1`.

2. **Update the checksum**:
   After pushing the git tag to GitHub (so `archive/vX.Y.Z.tar.gz` exists):
   ```bash
   cd packaging/aur
   updpkgsums
   ```

3. **Regenerate `.SRCINFO`**:
   The AUR requires `.SRCINFO` to match `PKGBUILD` exactly:
   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```

4. **Smoke-test the build locally**:
   ```bash
   makepkg -sfc
   ```
   This builds the wheel, executes the pytest suite in `check()`, installs into the package root, and ensures the package archive is valid.

5. **Push updates to AUR**:
   ```bash
   cd /path/to/aur-hyprconf2lua
   git pull
   cp /path/to/hyprconf2lua/packaging/aur/PKGBUILD .
   cp /path/to/hyprconf2lua/packaging/aur/.SRCINFO .
   git add PKGBUILD .SRCINFO
   git commit -m "chore: bump to vX.Y.Z"
   git push origin master
   ```

---

## 4. User Installation

Arch Linux / Omarchy users can install `hyprconf2lua` via their preferred AUR helper:

```bash
# Using paru
paru -S hyprconf2lua

# Using yay
yay -S hyprconf2lua
```
