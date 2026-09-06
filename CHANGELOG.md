# Changelog

All notable changes will be documented in this file.

The format is inspired by Keep a Changelog and Semantic Versioning.

## [3.0.0] - 2026-09-06

### Added
- Native Linux support:
	- `src/utils/app_paths.py` resolves the per-user data directory via `platformdirs` on every OS: `%LOCALAPPDATA%/DOTformat` on Windows and `~/.local/share/DOTformat` on Linux. Databases, backups, and the FFmpeg cache all follow this path automatically.
	- `src/utils/ffmpeg_finder.py` now downloads a static, self-contained FFmpeg build for Linux (amd64/arm64, via John Van Sickle's builds) when it isn't already on `PATH` or bundled, mirroring the existing Windows zip flow. Extracted binaries are marked executable (`chmod +x`) automatically.
	- `setup.py` builds the virtual environment and installs dependencies identically on Linux and Windows, resolving the venv's `bin/`/`Scripts/` layout per platform.
- Nuitka as a build backend:
	- New `src/utils/build_nuitka.py` compiles DOTformat into a standalone folder (`nuitka/main.dist/`) — or, with `onefile=True`, a single executable — with Tkinter, PIL, PyMuPDF, rembg, and onnxruntime bundled.
	- `PyMuPDF`/`fitz`, `numba`, `llvmlite`, and `pymatting` are deliberately excluded from Nuitka's C compilation (they either crash the compiler on large generated sources or rely on runtime source introspection). They're instead shipped as plain, uncompiled files under an `extra-libs/` folder via Nuitka's `--include-raw-dir` (which bypasses Nuitka's usual filtering-out of `.py`/`.so` files from bundled data, and goes through the same data embed/extract pipeline Nuitka uses for `--onefile`, so it places the files correctly whichever mode is used), imported at startup via a `sys.path` bootstrap in `main.py`.
	- `setup.py` now asks interactively whether to build with PyInstaller or Nuitka, with an optional low-memory mode for Nuitka on constrained machines.
- Refactored `src/utils/build_nuitka.py`'s low-memory toggle: it previously read a module-level `LOW_MEMORY_FLAG` from `setup.py` via `from setup import LOW_MEMORY_FLAG`, which (due to how that import interacted with `setup.py` being executed as `__main__`) always evaluated to `False` regardless of the user's answer — `--low-memory` was silently never applied. `build_nuitka()` now takes `low_memory` as a plain parameter.
- `build_nuitka()` also gained an `onefile` parameter (`--onefile` passed through to Nuitka). This replaced an earlier approach that copied the `extra-libs/` files into `main.dist/` as a post-build step: that only worked for `--standalone`, since `--onefile` seals its package *during* the Nuitka build itself, before any post-build copy could run — switching to `--include-raw-dir` (above) fixed this for both modes and let the whole post-build copy step be deleted.
- Fixed a major Nuitka build-time regression: `--jobs=1` was being passed unconditionally, forcing the ~1500 generated C files to compile one at a time regardless of how many CPU cores were available (a full build measured at ~26 minutes on a 16-core machine, effectively using one of them). `--jobs=1` is now only added when `low_memory=True` — serializing compilation is a deliberate trade-off for that mode, since each parallel `gcc` process adds to peak RAM use, which is exactly what low-memory mode exists to avoid. Everywhere else, `--jobs` is left unset so Nuitka defaults to using all available cores.
- PyInstaller spec generation and onefile/onedir choice:
	- New `src/utils/build_pyinstaller.py` renders `DOTformat.spec` from a template at build time instead of relying on a checked-in spec, and verifies the generated file (present, non-empty, contains the expected `Analysis`/`EXE` blocks, and parses as valid Python) before invoking PyInstaller against it.
	- The spec adapts to the host OS automatically (bundles `ffmpeg`/`ffprobe`/`ffplay` without the `.exe` suffix on Linux, only applies the `.ico` icon on Windows).
	- `setup.py` now asks whether the PyInstaller build should be a single file (`--onefile`-equivalent, one executable) or a one-folder build (a thin launcher plus a `dist/DOTformat/` folder of dependencies, avoiding onefile's slower startup extraction).
- Fixed Background Remover crashing in both PyInstaller build modes (onefile and onedir) with `PackageNotFoundError: No package metadata was found for pymatting`. The spec's `candidate_libs` called `collect_all('rembg')`, which only copies `rembg`'s own dist-info metadata, not its dependencies' — `pymatting` (rembg's alpha-matting dependency) reads its own version via `importlib.metadata.version(__name__)` at import time, and had no metadata bundled at all. `pymatting` is now included in `candidate_libs` directly.
- Admin user management UI: a full "View Users" screen (Options menu, admin only) lists all accounts and lets an admin create users, change roles, and delete users, each action gated behind re-entering the admin's password. Safeguards prevent demoting/deleting the base admin, deleting the last remaining admin, or changing your own role.
- Self-service "Change Password" dialog in the Options menu, re-wrapping the encryption master key under the new password automatically.
- Friendlier Background Remover diagnostics: missing/broken `rembg`, `numpy`, or `opencv-python-headless` now report the underlying exception type and message instead of a generic "missing dependency" note.
- Automated release builds: `.github/workflows/release.yml` triggers on every `v*` tag push and builds, on both Windows and Linux:
	- A PyInstaller onefile executable (`DOTformat-<tag>-windows.exe` / `DOTformat-<tag>-linux`, the latter a plain, directly runnable ELF binary).
	- A PyInstaller onedir standalone build, archived as `.zip` (Windows) / `.tar.gz` (Linux).
	- A Nuitka standalone build, archived as `.zip` (Windows) / `.tar.gz` (Linux).
	- All six assets are attached to a GitHub Release for that tag automatically.
- AUR packaging: added `packaging/aur/PKGBUILD` (package name `dotformat-bin`, following AUR convention for prebuilt-binary packages) plus a `.desktop` entry, installing the pre-built Nuitka standalone Linux tarball from GitHub Releases into `/opt/dotformat` with a `/usr/bin/dotformat` symlink, instead of compiling the heavy ML dependencies from source. See `packaging/aur/README.md` for the publish steps.

### Changed
- Major internal refactor of the GUI: the single 1,363-line `src/gui.py` was split into a `src/gui/` package —
	- `app.py` (window composition root and app lifecycle), `context.py` (shared app/session context passed to views),
	- `dialogs/` (`auth_dialog.py`, `history_dialog.py`),
	- `views/` (one file per feature: `image_view.py`, `background_view.py`, `pdf_view.py`, `audio_view.py`, `qr_view.py`, `video_view.py`, `options_view.py`, `help_view.py`),
	- `widgets/progress.py` (shared progress-dialog widget).
	- This mirrors the controller/service/repository split already used elsewhere in the codebase and removes the old `src/controllers/auth_controller.py` and `src/controllers/log_controller.py`, whose responsibilities moved into dedicated services (below) and the new dialogs.
- New service layer extracted from what used to be GUI-embedded logic:
	- `src/services/session_service.py`: owns the logged-in session state and the full master-key (K_APP)/database encryption-at-rest lifecycle (unwrap on login, atomic encrypt on logout/close, legacy-password fallback).
	- `src/services/auth_service.py`: login lockout policy (5 failed attempts → 5 minute lockout) and last-used-username persistence, with no UI dependency.
	- `src/services/log_service.py`: row fetching, filtering, sorting, CSV/XLSX exporting, and log maintenance (normalize IDs / restore backup) for the History dialog, independent of Tkinter.
	- `src/services/user_service.py` gained the full admin-management API (`list_users`, `create_user_by_admin`, `change_role`, `delete_user`, `change_own_password`), backed by new `UserRepository` methods (`find_by_id`, `list_all`, `count_admins`, `first_user_id`, `update_role`, `update_password_hash`, `delete`).
- Distribution: the Microsoft Store listing will be discontinued; Windows `.exe` builds continue to be published via GitHub Releases.
- `requirements.txt`: `pyreadline3` and `pywin32-ctypes` now carry a `sys_platform == "win32"` marker. Both packages have no usable distribution on Linux/macOS, so `pip install -r requirements.txt` would fail outright on Linux without this — a direct blocker for the native Linux support and Linux CI builds above.
- Packaging: dependency versions were unpinned in `requirements.txt` in favor of always installing the latest compatible release, since the previous 2023-era pins were increasingly hard to resolve on current Python/OS combinations; `nuitka` was added as a build dependency alongside `pyinstaller`.
- `.gitignore`: build output directories are now matched broadly (`dist*/`, `nuitka/`), and `*.so`/`*.spec` files are ignored (Linux shared objects and locally generated PyInstaller spec files).

### Removed
- `DOTformat.spec` (the checked-in PyInstaller spec file) was removed from the repository; PyInstaller builds now generate their spec on demand, and Nuitka is the primary recommended build path going forward.
- `src/controllers/` package (`auth_controller.py`, `log_controller.py`): superseded by the `src/gui/dialogs/` + `src/services/` split described above.
- Compiled `__pycache__` artifacts that had been accidentally committed under `src/__pycache__` and `src/models/__pycache__`.

## [2.1.3] - 2025-10-28

### News
- App released on Microsoft Store

## [2.1.2] - 2025-10-26
### Fixed
- Background Remover (Windows 11, packaged/no-console builds):
	- Resolved intermittent crash with the message "'NoneType' object has no attribute 'write'" by safely redirecting `sys.stdout`/`sys.stderr` to `os.devnull` when they are `None` in frozen apps. Some native libraries attempt to write to these streams during initialization and previously caused a hard failure.

### Added
- Dependency preflight for Background Remover:
	- Before opening the progress dialog, the app now checks for required AI libraries (`rembg`, `numpy`, `opencv-python-headless`). If any are missing, it shows a friendly message explaining that the portable build doesn't bundle heavy ML dependencies and how to enable the feature when running from source.
	- Missing-dependency details are recorded in the conversion log for easier QA.

### Changed
- UX: When dependencies are missing, the feature no longer displays a progress window that sits around ~90% (“Loading AI libraries…”) and then errors. Instead, it exits early with a clear explanation and no progress dialog.

## [2.1.1] - 2025-10-26

### Added
- Privacy & Terms:
	- Added `PRIVACY_POLICY.md` and `TERMS.md` to the repository.
	- In-app “Privacy & Terms” dialog with first-run consent to review and accept before using the app.
- Image conversion:
	- Output folder chooser for image format conversion. Converted images from a batch are saved to the selected directory.

### Fixed
- Audio → Text (Windows 11):
	- Suppressed flashing console windows by spawning FFmpeg subprocesses with no-window flags during preprocessing and chunked transcription.
- Image → PDF (Windows):
	- Fixed failures when source images have transparency (RGBA/LA/P). Images are now flattened to RGB automatically before building the PDF.
- PDF Password:
	- When attempting to protect an already encrypted/protected PDF, the app now shows a clear explanatory message and avoids a false success.
- User Management:
	- Prevented changing your own role (even if not the last admin) to avoid accidental lockouts.
- Video conversion (Windows 11):
	- Suppressed visible console windows launched by FFmpeg to prevent CMD flashes during conversions.

### Changed
- Options dialog:
	- Removed the “Export My Data” and “Delete My Data” buttons per feedback. Privacy documents remain accessible via the “Privacy & Terms” entry. Log export continues to be available from the Log viewer.
- Progress polish:
	- Minor refinements so progress bars advance smoothly and reliably complete at 100%.

## [2.1.0] - 2025-10-24

### Added
- PDF → PNG: Quality selector (DPI slider 100–500, default 300, with recommended marker) before exporting images.
- FFmpeg helper: Optional in-app downloader with a "What is FFmpeg?" explanation dialog; stores a portable copy under %LOCALAPPDATA%/DOTformat/ffmpeg/bin.
- Audio → Text: Language selector in the GUI (BCP‑47 codes; persisted between runs). Default is pt‑BR.
 - Progress UX: Determinate/staged progress for multiple features.
	 - Audio → Text: Determinate bar driven by ~10s chunks.
	 - Remove Background: Determinate staged bar (Loading → Applying AI model → Finalizing).
 - Log maintenance: Normalize IDs action in the Log viewer. Renumbers `conversion_log` so the oldest entry is ID=1 and IDs increase chronologically. Includes a determinate progress dialog and preserves all data.
 - Log maintenance: Restore Old Log action in the Log viewer to revert to the pre‑normalization table snapshot (`conversion_log_old`).

### Fixed
- PDF → PNG conversion failed on Windows with the message "Unable to get page count. Is poppler installed and in PATH?" when attempting to export images.
- Audio → Text and Video conversion: FFmpeg not found even when bundled in project; improved detection and process PATH setup.
 - Model-side logging completeness: remove background, image conversion, and single video conversion now record input/output paths and errors consistently.

### Changed
- Rewrote `pdf_to_png` implementation to use PyMuPDF (`fitz`) instead of `pdf2image`/Poppler.
 - Centralized FFmpeg resolution in `src/utils/ffmpeg_finder.py`. New search order: project bundle (DOTformat/ffmpeg/bin) → system PATH → %LOCALAPPDATA%/DOTformat/ffmpeg/bin → PyInstaller bundle. When not available, the app can prompt to download a portable FFmpeg and prepend its bin folder to the process PATH.
 - Reworked `convert_audio_to_text` to improve robustness: always converts inputs to WAV 16 kHz mono 16‑bit, normalizes loudness, and splits long audio into ~50s chunks before sending to the recognizer. The function now accepts a `language` parameter (default `'pt-BR'`). The GUI passes the selected language.
 - Video conversion progress is smoother: parsing-based progress is capped to keep headroom for finalization and a gentle advancement prevents the bar from appearing frozen around 80–90%.
 - Audio language list in the GUI is now displayed alphabetically.
 - Startup behavior: removed automatic log normalization on app launch. Normalization is now a manual action from the Log viewer.
 - Database maintenance safety: normalization keeps a snapshot (`conversion_log_old`), and a SQLite busy timeout is set to reduce transient lock stalls.
 - Authentication UX: Press Enter to submit on Login and Registration, with smarter initial focus (password when username is prefilled).

### Details
- FFmpeg resolution and download flow:
	- Previous behavior: Each feature tried bespoke logic (or just 'ffmpeg' on PATH). Users could hit errors like "FFmpeg não encontrado" despite having the binary in the project.
	- New logic: `ensure_ffmpeg()` consolidates lookup and, if not found, offers to download a portable build to the user's data directory without admin rights. Once placed, the helper prepends that bin directory to the process PATH and returns the absolute paths to `ffmpeg.exe` and `ffprobe.exe`.
	- A small UI includes a "What is FFmpeg?" button with an explanation so users understand why it's needed.

- Audio → Text pipeline:
	- Inputs are normalized and resampled to WAV 16 kHz mono 16‑bit to reduce recognizer failures and improve accuracy.
	- Long recordings are chunked into ~10s segments para progresso suave e para evitar erros "Bad Request"; errors and then concatenated.
	- The language used by the recognizer can be chosen from the GUI and is remembered between runs.
	- Supported audio extensions are centralized in `SUPPORTED_EXTENSIONS` in `audio_to_text.py`, and the GUI file dialog consumes the same list to keep both sides in sync.

- Previous behavior:
	- The function `pdf_to_png(pdf_file, output_dir)` called `pdf2image.convert_from_path`, which relies on external Poppler binaries on Windows. If Poppler was not installed or not present on PATH, calling the feature would raise an exception at save time (the dialog appeared, but the conversion failed with the poppler error).

- New logic:
	- `pdf_to_png` now opens the PDF with `fitz.open(pdf_file)` and renders each page to a PNG using a `fitz.Matrix` computed from a DPI scale (default 200 DPI). Each page is saved to `page_<n>.png` under the chosen output directory.
	- API contract preserved: the function still returns `(success: bool, message: str)`, and does not change the GUI call sites.
	- Output directory is created when missing; images are written without any external dependencies.

- Database maintenance – Normalize IDs:
	- Problem: After imports and deletes over time, `conversion_log` IDs could be non-sequential or start at a high value, confusing users.
	- New tool: `normalize_conversion_log_ids(progress)` rebuilds the table in chronological order and assigns fresh sequential IDs starting from 1, preserving all rows and data.
	- UX: Launched from the Log viewer via a "Normalize IDs" button. Runs in a background thread and shows a determinate progress dialog. On completion, the Log view refreshes automatically.
 	- Safety: The original table is preserved as `conversion_log_old` and can be restored via the "Restore Old Log" button in the Log viewer.

- Why this fix:
	- Removes the external Poppler requirement, which is brittle for end users and for packaged builds. PyMuPDF is already included in `requirements.txt` and works out of the box on Windows.

- Notes / implications:
	- Default DPI is 200. Higher DPI (e.g., 300) yields larger images and slower rendering; can be made configurable later via the GUI if desired.
	- Encrypted PDFs will fail to open unless unlocked; future work could prompt for a password and authenticate the document before rendering.
	- No changes required to packaging. `pymupdf` (PyMuPDF) is already pinned; no spec changes needed.

## [2.0.0] - 2025-10-09

This release is a major update over 1.2.1 with authentication, safer data handling, progress across operations, and many UX improvements.

### Added
- Authentication and roles
	- Local user authentication before accessing features (PBKDF2‑HMAC‑SHA256 with per‑user salt; no plaintext storage).
	- Role‑based permissions: first user is admin (can view History/Log and manage users); others default to user.
	- Add User flow inside the app; admin creates users and a per‑user key wrapper is provisioned immediately.
	- Login lockout policy: after 5 failed attempts, the user is locked for a period (configurable). Test default is 10 seconds. Configure at `src/controllers/auth_controller.py` using:
		- `LOCKOUT_MAX_ATTEMPTS`
		- `LOCKOUT_DURATION_SECONDS`

- Encrypted database and backups
	- Envelope key architecture: a random master key (K_APP) is wrapped per user (AES‑EAX + PBKDF2). Password changes do not require re‑encrypting the whole DB.
	- Optional on‑close encryption: the plaintext DB is atomically encrypted to a `.dotf` file and the plaintext is wiped best‑effort.
	- Automatic backups on exit to `%LOCALAPPDATA%/DOTformatBackups/<timestamp>` and automatic restore on startup if DBs are missing/corrupt.
	- Backup retention keeps only the latest 2 backups.

- Log Viewer (History)
	- Search box and status filter (All/Success/Error) applied client‑side.
	- Sortable columns with ascending/descending toggle.
	- Export only the currently filtered rows to CSV or XLSX (uses openpyxl when available). Default filename `DOTformat_Log_YYYYMMDD-HHMMSS` and initial directory is Downloads.
	- Conversion log details are compacted (single line up to ~140 chars) and statuses normalized to lowercase.
	- Admin operations log with rich detail (actor/target IDs in actions like create user, change role, delete user).

- Progress and UX
	- Generic progress modal with determinate 0–100 bar. Single‑shot actions show gentle auto‑advance to ~92% and jump to 100% on finish.
	- Step‑based progress for batch video conversions.
	- Progress dialog cannot be closed mid‑task to prevent errors from partial results.
	- “?” Help button with concise feature descriptions (English‑only UI).
	- File dialogs remember the last used folder per feature (PDF, images, audio, QR, video, remove background).

- Features and conversions
	- Image conversion: handles PNGs with transparency when saving as JPEG (flattens onto white background); adds per‑batch progress dialog and clearer partial success messages.
	- Background removal: shows an indeterminate progress dialog during processing; post‑processing tools include Clean Mask, Fill Holes, Smooth Edges, and a Manual Eraser with zoom/pan and undo.
	- Video conversion: switched to calling the bundled `ffmpeg` binary via subprocess; supports single conversion with live progress (parsed from ffmpeg stderr) and batch conversion with step‑based progress.
	- QR Code generation: stabilized and remembers last save directory.

### Changed
- Data storage and paths
	- Centralized per‑user data directory via platformdirs; databases live under the OS user data path (e.g., AppData on Windows). One‑time migration from legacy location when detected.
	- Portable mode was removed; the app now consistently uses OS user data paths.

- UI/Flow
	- Logout is in‑memory: the UI is torn down and the login screen is rebuilt without restarting the process.
	- Options dialog no longer grabs focus modally; it auto‑closes after action execution.
	- README was restructured (Installation, Project Structure) and a proper detailed `CHANGELOG.md` was introduced.
	- Requirements were curated so core/light deps install first; heavy/optional deps are lazy‑loaded by the features that need them (e.g., rembg for background removal).

### Fixed
- Prevented accidental blank DB creation by improving decrypt + schema‑init ordering.
- Resolved GUI freeze perception during background removal by adding a progress dialog.
- Fixed “cannot unpack non‑iterable NoneType object” in progress flows by enforcing strict `(bool, str)` returns and preventing progress window closure mid‑task.
- Fixed `ffmpeg` runtime error “module 'ffmpeg' has no attribute 'input'” by removing the Python `ffmpeg` package dependency and calling the `ffmpeg.exe` binary directly.
- Fixed JPEG saves for images with transparency by flattening RGBA/LA/P images to RGB before writing.

### Removed
- Portable mode support (environment flag and setup switch). All data is stored under the OS user data directory.

### Security
- Encrypted file format includes a magic header, version, salt, nonce, authentication tag, and ciphertext; integrity is ensured via AEAD (AES‑EAX).
- Password hashing uses PBKDF2‑HMAC‑SHA256 with per‑user salts.
- No password recovery mechanism is provided.
- Plaintext DB wipe after encryption is best‑effort and filesystem‑dependent.

### Developer Experience
- Introduced service and repository layers for logging and users.
- Clear separation between controllers, models, services, repositories, and utils.
- Added `main.py` entry point and improved `DOTformat.spec`.

### Breaking changes
- Portable mode removed; data is stored under the OS user data dir (AppData on Windows).
- Status strings in logs are now lowercase (`success`/`error`).
- Video conversion requires an `ffmpeg` binary; the build includes one under `ffmpeg/bin/ffmpeg.exe`, with fallback to system `ffmpeg` if not found.

Migration notes
- On first launch, the app attempts to restore databases if missing/corrupt and migrates legacy data to the new data directory.
- If you previously relied on portable behavior, remove the env flag and plan for OS user data paths.

## [1.2.1] - 2025-10-06

(See earlier changes on [README](./README.md).)

## [1.2.0] - 2025-06-18

(See earlier changes on [README](./README.md).)

## [1.1.0] - 2025-06-17

(See earlier changes on [README](./README.md).)

## [1.0.0] - 2025-06-13

Initial release.
