# Publishing `dotformat-bin` to the AUR

This `PKGBUILD` installs the pre-built Linux Nuitka standalone tarball from a
GitHub Release (produced by `.github/workflows/release.yml`) into `/opt/dotformat`,
with a `dotformat` launcher symlinked into `/usr/bin` and a desktop entry.

It's named `dotformat-bin` per AUR convention for packages that ship a
prebuilt binary instead of compiling from source (`provides`/`conflicts` on
plain `dotformat` are set so it can't be installed alongside a hypothetical
future source-based `dotformat` package).

## Before the first publish

1. Push a version tag (e.g. `v3.0.1`) and wait for the "Release builds" workflow
   to finish and attach its assets to the GitHub Release.
2. Update `pkgver` in `PKGBUILD` to match the tag (without the leading `v`).
3. Compute the real checksums and replace the placeholders:

   ```bash
   curl -LO "https://github.com/EdynuT/DOTformat/releases/download/v${pkgver}/DOTformat-v${pkgver}-linux-nuitka-standalone.tar.gz"
   sha256sum "DOTformat-v${pkgver}-linux-nuitka-standalone.tar.gz" packaging/aur/dotformat.desktop
   ```

   Paste the two hashes into `sha256sums=(...)`, in the same order as `source=(...)`.
4. Test the build locally in a clean Arch container/chroot:

   ```bash
   cd packaging/aur
   makepkg -si
   ```

## Publishing

AUR packages live in their own git repository per package name, separate from
this repo.

```bash
git clone ssh://aur@aur.archlinux.org/dotformat-bin.git aur-dotformat-bin
cp packaging/aur/PKGBUILD packaging/aur/dotformat.desktop aur-dotformat-bin/
cd aur-dotformat-bin
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD dotformat.desktop .SRCINFO
git commit -m "dotformat-bin 3.0.0-1"
git push
```

(Requires an AUR account with an SSH key registered at https://aur.archlinux.org/.)

## On every future release

1. Bump `pkgver` (and reset `pkgrel=1`), or bump `pkgrel` only for a packaging-only fix.
2. Recompute `sha256sums` for the new tarball.
3. Regenerate `.SRCINFO` and push, as above.
