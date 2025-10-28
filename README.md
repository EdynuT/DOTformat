# DOTFORMAT

DOTFORMAT is a Python project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 2.1.3

## Changelog

### 2.1.3 

- App released on Microsoft Store

## Past releases:

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

- **Optional Encrypted Log Storage:** Before exiting you may encrypt the SQLite log database with a password. If encrypted, you will be prompted to decrypt on next launch; skipping creates a fresh empty log instead.
    - Log maintenance: from Conversion History, use “Normalize IDs” to fix legacy logs where IDs are reversed (oldest had the largest ID). This operation only renumbers IDs by creation time and keeps all rows and details intact.
        - Manual and safe: normalization does NOT run automatically on startup. You decide when to run it.
        - Reversible: use “Restore Old Log” to revert to the prior table snapshot if you change your mind.

## Project Structure

The project structure is organized as follows:

```text
DOTFORMAT/
├── src/
│   ├── images/                 # Image resources (icons, etc.)
│   │   ├── image.ico
│   │   └── image.png
│   ├── controllers/            # UI controllers
│   │   ├── auth_controller.py  # Login/registration, roles
│   │   └── log_controller.py   # Log viewer (filter/sort/export)
│   ├── db/                     # Database connections/adapters
│   │   ├── connection.py       # Main log DB connection
│   │   ├── auth_connection.py  # Auth DB connection
│   │   └── maintenance.py      # Log IDs maintenance
│   ├── repositories/           # Data access layer
│   │   ├── conversion_repository.py
│   │   └── user_repository.py
│   ├── services/               # Business logic
│   │   ├── conversion_service.py
│   │   └── user_service.py
│   ├── models/                 # Feature scripts
│   │   ├── audio_to_text.py
│   │   ├── convert_image.py
│   │   ├── convert_video.py
│   │   ├── pdf_manager.py
│   │   ├── qrcode_generator.py
│   │   └── remove_background.py
│   ├── utils/                  # Helpers/utilities
│   └── gui.py                  # Graphical user interface (Tkinter)
├── CHANGELOG.md                # Program detailed changes and updates
├── DOTformat.spec              # PyInstaller spec file
├── LICENSE                     # Project license
├── main.py                     # Program entry point
├── PRIVACY_POLICY.md           # Privacy Policy
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── setup.py                    # Setup/build script (venv + exe)
└── TERMS.md                    # Terms & Conditions
```

## Requirements

- python < 3.11

## Installation

Follow these steps on Windows (PowerShell) to set up the environment and optionally build the executable.

1) Clone the repository

```powershell
git clone https://github.com/EdynuT/DOTformat.git
cd DOTformat
```

2) One‑shot setup (recommended)

```powershell
python .\setup.py
```

This will create a virtual environment, install dependencies, and build the executable in `dist/`.

Notes:
- Default data location:
    - Windows: %LOCALAPPDATA%\DOTformat
- During build, the log may appear to stall at:

    ```
    Building PKG (CArchive) DOTformat.pkg
    ```

Don't worry, the file is a little larger than normal, so it takes a few minutes to build.

## Changes

- If any unofficial changes are made to the project (such as adding a new script), it is recommended to update the .spec file:

```sh
cd DOTformat
pyi-makespec --name DOTformat --onefile --windowed main.py
```

- Then, create the executable file:

```sh
pyinstaller DOTformat.spec
```

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

Background Remover in 2.x works best when running from source with the extra AI libraries installed:

- Install: `pip install rembg numpy opencv-python-headless`
- The portable EXE intentionally does not include these heavy packages; if they’re missing, the app will show a quick message explaining how to enable the feature.

For the most recent fixes and security updates, use DOTFORMAT >= 2.0.0. 

I occasionally ship small bug fixes between feature releases.