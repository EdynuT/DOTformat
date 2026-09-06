# DOTFORMAT

DOTFORMAT is a Python project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 3.0.0

## Changelog

### 3.0.0

- **Native Linux support:** DOTformat now runs, builds, and stores its data natively on Linux, not just Windows.
    - App data (databases, backups, FFmpeg cache) is resolved per‑OS via `platformdirs`: `%LOCALAPPDATA%\DOTformat` on Windows, `~/.local/share/DOTformat` on Linux.
    - FFmpeg auto‑download now supports Linux (amd64/arm64 static builds) in addition to Windows, with the extracted binaries made executable automatically.
    - `setup.py` builds the virtual environment and installs dependencies the same way on both platforms.

- **New build backend: Nuitka.** `setup.py` can now build a standalone executable with either PyInstaller or Nuitka (asked interactively), with an optional low‑memory mode for constrained machines.

- **Smarter PyInstaller builds.** The checked‑in `DOTformat.spec` was removed; `setup.py` now generates and verifies a spec on the fly for the current OS, and lets you choose between a single‑file executable or a one‑folder build.

- **Admin: full user management.** The Options menu now includes a "View Users" screen (admin only) to create users, change roles, and delete users — each action requires re‑entering the admin password, and the base admin/last remaining admin are protected from being demoted or removed. A self‑service "Change Password" dialog was also added for any account.

- **Major internal refactor.** The old single‑file `src/gui.py` was split into a `src/gui/` package (composition root, dialogs, one view module per feature, shared widgets), and session/auth/log business logic that used to live in the UI now lives in dedicated services (`session_service.py`, `auth_service.py`, `log_service.py`). This has no visible effect on functionality but makes the codebase easier to extend and test.

- **Improved diagnostics** for the Background Remover: missing or broken AI dependencies (`rembg`, `numpy`, `opencv-python-headless`) now report the actual underlying error.

- Dependency versions in `requirements.txt` are no longer hard‑pinned, so installs always pick the latest compatible releases.

- The Microsoft Store listing will be discontinued; Windows users can keep getting the `.exe` file from [Releases](https://github.com/EdynuT/DOTformat/releases/latest).

## Past releases:

### 2.1.3 

- App released on Microsoft Store

### 2.1.2

- Fixed a crash that could occur on Windows 11 packaged builds with the error "'NoneType' object has no attribute 'write'". In no‑console builds, some native libraries try to write to stdout/stderr, which can be `None`. We now silence those streams internally so the feature runs safely.

### 2.1.1

- Added Privacy Policy and Terms documents.

- Fixed various bugs and small improvements.

### 2.1.0

- Fixed: PDF to PNG not generating images on Windows (removed Poppler dependency; now renders with PyMuPDF).

- Fixed: FFmpeg detection for Audio to Text and Video conversion (now checks project bundle, PATH, then LocalAppData; optional guided download).

- Added: Audio → Text language selector (BCP‑47, saved between runs) and more robust transcription pipeline (converts to WAV 16 kHz mono 16‑bit, normalizes volume, splits long audio into ~50s chunks).
    - Default language set to pt‑BR; you can choose others like en‑US, en‑GB, es‑ES, es‑MX, fr‑FR, de‑DE, it‑IT, ja‑JP, ko‑KR, ru‑RU.

- Improved: Progress UX
    - Audio → Text: determinate bar driven by 10s chunks (progresso mais fluido e previsível).
    - Video conversion: barra mais suave com avanço durante etapas silenciosas do ffmpeg (evita ficar “presa” em 80–90%).
    - Remove Background: barra determinística com estágios (“Loading image…”, “Applying AI model…”, “Finalizing…”).

- Added: Database maintenance for logs
    - “Normalize IDs” button in Conversion History renumbers log IDs so the oldest entry is ID=1 and newer entries follow sequentially. A progress dialog shows the update; no data/order is lost.
    - New: “Restore Old Log” button to revert to the pre‑normalization table snapshot if you want to undo.
    - Change: automatic normalization at startup was removed; normalization is manual via the Log screen only.
    - Stability: SQLite busy timeout applied during maintenance to avoid temporary lock stalls.

- Improved: Authentication UX
    - You can press Enter to submit both Login and first‑time Registration dialogs.
    - Smarter initial focus: when the username is prefilled, the cursor starts in the password box.

### 2.0.0

- Sign‑in with roles
    - Log in before using features; the first account becomes admin, others are standard users.
    - Optional lockout after repeated failed attempts to keep accounts safe.

- Clear progress everywhere
    - Determinate progress bars for long‑running tasks; batch video shows per‑file progress.
    - Background removal now shows a progress window, so the app won’t feel frozen.

- Smoother workflow
    - PDF Manager in one place (PDF → DOCX, PDF → PNG, Add password).
    - File dialogs remember the last folder you used per feature.
    - “?” Help button with short in‑app tips.

- Better conversions
    - Images: transparent PNGs convert nicely to JPEG (auto‑fills a background).
    - Videos: more reliable conversions with live progress.
    - QR Code: simpler flow that remembers your save location.

- History and export
    - Log viewer with search, status filter, sorting, and export of the current view (CSV/XLSX).

- Stability and safety
    - Automatic backups on exit and automatic restore on startup if needed.
    - Consistent app‑data location (portable mode removed).

### 1.2.1: 

- Reorganized requirements.txt to install lighter/core dependencies first and heavy scientific/ML stack (Pillow, NumPy, numba/llvmlite, onnxruntime, opencv, scikit-image, scipy) at the end to reduce resolver breakage.

- Added lazy import strategy for background removal (now rembg, numpy, cv2 only load when the feature is invoked) preventing startup crashes if those packages are absent.

- Clarified optional nature of rembg (kept commented so regular users can install faster / fewer issues).

- Improved error messaging for missing heavy dependencies (friendly instructions instead of hard tracebacks).

- General dependency stability fixes for Python 3.10 builds (older compatible pins; avoided NumPy 2 x incompatibilities).

### 1.2.0: 

- (Finally) Added the PDF Password to the user interface in the pdf_manager_action function. (How did I forget about this all this time?)

- Merged the PDF files (pdf_to_png.py, pdf_to_docx.py, and pdf_password.py) into a single one called pdf_manager.py to keep the code clean.

- Added a background remover script using the rembg library. See the Features section for more details.

- Added a main.py file for easier access to the program's entry point.

- Moved the setup.py file from the src folder to the main folder for easier access to the setup script.

- Improved the video converter with a real-time progress bar and the ability to cancel conversion during processing.

- Improved compatibility with other systems in general.

### 1.1.0: 

- The folder name converters was changed to models.

- Compatibility bug fixes with other system languages (PT-BR).

- Automatic installation of ffmpeg and autonomous addition to the system PATH.

- Code translation to English and added some comments for better general understanding.

- Possibility of converting videos to other formats besides MP4.

### 1.0.0: 

- Initial public release.

#### Note

> See full details in [CHANGELOG.md](./CHANGELOG.md)

## Features

Below are the features currently available:

- **Audio to Text Conversion:** Transform audio files into text using speech recognition.
    - Now with language selector (default pt‑BR), sorted alphabetically.
    - Robust preprocessing: áudio é convertido para WAV 16 kHz mono 16‑bit e normalizado; áudios longos são divididos em partes (~10s) para progresso mais suave e menos erros.
    - Determinate progress bar: avança a cada chunk processado e fecha em 100% ao concluir.

- **Image Conversion:** Convert images to different formats and resolutions.

- **PDF to PNG:** Convert PDF documents into PNG images for easy viewing.

- **PDF to Word (.docx):** Convert PDFs into editable Word documents.
(This script may have formatting issues when the PDF has tables or when the text is blurry.)

- **PDF Passwords:** Set a password for a chosen PDF file for better security.

- **QR Code Generator:** Create QR codes from inserted text.

- **Video Conversion:** Convert videos from any format to MP4, AVI, or MOV for better usability.

    - MP4 for better image resolution. Most common for everything.

    - AVI for higher frame rate at the expense of quality.

        - MOV for good resolution and frame rate.
    - Smoother progress: a barra continua avançando mesmo durante etapas silenciosas (mux/finalização) e encerra em 100% ao concluir.

(This script uses more CPU and RAM than usual. Older systems may experience some slowness when using it, but it will work.)

- **Remove Background:** Removes the background of the image you choose, with advanced post-processing options:
    - Determinate progress: mostra estágios e avança suavemente durante a inferência.

    - **Post-processing tools:** Clean mask, fill small holes, and smooth edges with one click.

    - **Manual Eraser Mode:** After automatic background removal, you can manually erase or restore areas of the image using a configurable brush.

        - Adjustable brush size (vertical slider from 1 to 100, with visual indicators).
        - Brush preview follows the mouse cursor.
        - Zoom in/out with mouse scroll (up to 500%), centered on the cursor.
        - Pan the image by dragging with the right mouse button.
        - Undo last manual actions.
        - Option to save or discard manual edits before returning to the main window.

- **Local Authentication & Audit:** Users must log in (or register first user) before accessing features. All feature executions are logged and associated with the username.
    - Press Enter to submit Login/Registration; faster flow without clicking the button.
    - Initial focus goes to the password field when the username is prefilled.
    - Login lockout: after 5 failed attempts, the account is temporarily locked out for 5 minutes.

- **Admin: User Management:** Admins get a "View Users" screen (Options menu) listing every account, with actions to create users, change roles (user ⇄ admin), and delete users — each guarded by re‑entering the admin password.
    - The base admin account and the last remaining admin can't be demoted or deleted, to prevent accidental lockouts.
    - Any user can change their own password from the Options menu; this also re‑wraps the database encryption key under the new password.

- **Optional Encrypted Log Storage:** Before exiting you may encrypt the SQLite log database with a password. If encrypted, you will be prompted to decrypt on next launch; skipping creates a fresh empty log instead.
    - Log maintenance: from Conversion History, use “Normalize IDs” to fix legacy logs where IDs are reversed (oldest had the largest ID). This operation only renumbers IDs by creation time and keeps all rows and details intact.
        - Manual and safe: normalization does NOT run automatically on startup. You decide when to run it.
        - Reversible: use “Restore Old Log” to revert to the prior table snapshot if you change your mind.

## Project Structure

The project structure is organized as follows:

```text
DOTFORMAT/
├── .github/
│   └── workflows/
│       └── release.yml         # Tag-triggered build/release pipeline (Windows + Linux)
├── packaging/
│   └── aur/                    # Arch Linux (AUR) package: PKGBUILD, .desktop, publish guide
├── src/
│   ├── images/                 # Image resources (icons, etc.)
│   │   ├── image.ico
│   │   └── image.png
│   ├── gui/                    # Graphical user interface (Tkinter)
│   │   ├── app.py              # Composition root: main window + app lifecycle
│   │   ├── context.py          # Shared app/session context passed to views
│   │   ├── dialogs/
│   │   │   ├── auth_dialog.py      # Login/registration dialog
│   │   │   └── history_dialog.py   # Conversion history/log viewer
│   │   ├── views/               # One module per feature button
│   │   │   ├── image_view.py
│   │   │   ├── background_view.py
│   │   │   ├── pdf_view.py
│   │   │   ├── audio_view.py
│   │   │   ├── qr_view.py
│   │   │   ├── video_view.py
│   │   │   ├── options_view.py     # Options menu, user management
│   │   │   └── help_view.py        # Help + Privacy/Terms dialogs
│   │   └── widgets/
│   │       └── progress.py     # Shared determinate/indeterminate progress dialog
│   ├── db/                     # Database connections/adapters
│   │   ├── connection.py       # Main log DB connection
│   │   ├── auth_connection.py  # Auth DB connection
│   │   └── maintenance.py      # Log IDs maintenance
│   ├── repositories/           # Data access layer
│   │   ├── conversion_repository.py
│   │   └── user_repository.py
│   ├── services/               # Business logic
│   │   ├── conversion_service.py
│   │   ├── user_service.py     # Registration, auth, admin user management
│   │   ├── session_service.py  # Session state + DB encryption lifecycle
│   │   ├── auth_service.py     # Login lockout policy, last-user persistence
│   │   └── log_service.py      # History filtering/sorting/export/maintenance
│   ├── models/                 # Feature scripts
│   │   ├── audio_to_text.py
│   │   ├── convert_image.py
│   │   ├── convert_video.py
│   │   ├── pdf_manager.py
│   │   ├── qrcode_generator.py
│   │   └── remove_background.py
│   └── utils/                  # Helpers/utilities
│       ├── app_paths.py        # Per-OS data directory (Windows/Linux)
│       ├── ffmpeg_finder.py    # FFmpeg discovery/download (Windows/Linux)
│       └── build_nuitka.py     # Nuitka build steps used by setup.py
├── CHANGELOG.md                # Program detailed changes and updates
├── LICENSE                     # Project license
├── main.py                     # Program entry point
├── PRIVACY_POLICY.md           # Privacy Policy
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── setup.py                    # Setup/build script (venv + exe, PyInstaller or Nuitka)
└── TERMS.md                    # Terms & Conditions
```

## Installation

DOTformat runs natively on both Windows and Linux. Clone the repository, then run the one‑shot setup script for your platform.

1) Clone the repository

```bash
git clone https://github.com/EdynuT/DOTformat.git
cd DOTformat
```

2) One‑shot setup (recommended)

On Windows (PowerShell):

```powershell
python .\setup.py
```

On Linux:

```bash
python3 setup.py
```

This creates a virtual environment, downloads FFmpeg automatically if it isn't already available, installs dependencies, and then asks which build backend to use:

- **1 – PyInstaller:** generates a fresh `DOTformat.spec` for your OS and asks whether to build a single file (one executable, simplest to distribute) or a one‑folder build (`dist/DOTformat/`, a launcher plus its dependencies — starts faster since nothing needs to be unpacked first).
- **2 – Nuitka (recommended):** compiles a standalone, self‑contained folder under `nuitka/main.dist/`. You'll be asked whether to enable low‑memory mode, useful on machines with limited RAM.

Notes:
- Default data location (databases, backups, FFmpeg cache):
    - Windows: `%LOCALAPPDATA%\DOTformat`
    - Linux: `~/.local/share/DOTformat`
- To run from source without building an executable, just install the requirements (`pip install -r requirements.txt`) into a virtual environment and run `python main.py`.
- Nuitka builds can take several minutes and use significant RAM/CPU while compiling; this is expected.

### Prebuilt downloads

Pushing a `v*` tag runs [`.github/workflows/release.yml`](.github/workflows/release.yml), which builds DOTformat with both PyInstaller and Nuitka on Windows and Linux and publishes everything to that tag's [GitHub Release](https://github.com/EdynuT/DOTformat/releases): a Windows `.exe`, a Linux binary, and standalone `.zip`/`.tar.gz` builds for each backend.

Arch Linux users will be able to install the `dotformat-bin` package from the AUR once published (see [packaging/aur/](./packaging/aur/)), which installs the prebuilt Nuitka Linux build.

## Contributions

I welcome contributions to improve DOTFORMAT!  
If you'd like to contribute, please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write clear, concise commit messages.
4. Ensure that your code follows the existing style and is well commented.
5. Submit a pull request describing your changes and why theyâ€™re needed.

## License

MIT License

## Message

Background Remover works best when running from source (or a Nuitka build, which bundles it) with the extra AI libraries installed:

- Install: `pip install rembg numpy opencv-python-headless`
- A minimal PyInstaller build may intentionally skip these heavy packages; if they're missing or broken, the app will show a message explaining the exact error and how to enable the feature.

For the most recent fixes, native Linux support, and security updates, use DOTFORMAT >= 3.0.0.

I occasionally ship small bug fixes between feature releases.