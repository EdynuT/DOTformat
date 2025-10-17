# Changelog

All notable changes will be documented in this file.

The format is inspired by Keep a Changelog and Semantic Versioning.

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
