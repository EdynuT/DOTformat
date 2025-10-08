# DOTFORMAT

DOTFORMAT is a Python project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 1.2.1

### Changelog
Keep a concise overview here; full historical and in‑progress details live in `CHANGELOG.md`.

Latest (Developing / Unreleased highlights):
- Local authentication & role-based access (admin vs user)
- Key wrapping architecture (per-user AES-EAX wrapped master key)
- Optional encrypted log database with atomic on-close encryption
- In‑memory logout (no full process restart) and secure session rebuild
- Log viewer with filter / search / sort + filtered export (CSV/XLSX)
- Centralized per-user data directory & legacy auto-migration

Past releases (summary):
- 1.2.1: Dependency loading improvements, lazy heavy imports, clearer optional packages, stability fixes.
- 1.2.0: PDF password UI, unified PDF manager, background remover feature, improved video converter.
- 1.1.0: Folder restructure (converters→models), ffmpeg auto-setup, multi-language fixes, more video formats.
- 1.0.0: Initial public release.

See full details: [CHANGELOG.md](./CHANGELOG.md)

## Features

Below are the features currently available:

- **Audio to Text Conversion:** Transform audio files into text using speech recognition.

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

(This script uses more CPU and RAM than usual. Older systems may experience some slowness when using it, but it will work.)

- **Remove Background:** Removes the background of the image you choose, with advanced post-processing options:

    - **Post-processing tools:** Clean mask, fill small holes, and smooth edges with one click.

    - **Manual Eraser Mode:** After automatic background removal, you can manually erase or restore areas of the image using a configurable brush.

        - Adjustable brush size (vertical slider from 1 to 100, with visual indicators).
        - Brush preview follows the mouse cursor.
        - Zoom in/out with mouse scroll (up to 500%), centered on the cursor.
        - Pan the image by dragging with the right mouse button.
        - Undo last manual actions.
        - Option to save or discard manual edits before returning to the main window.

- **Local Authentication & Audit:** Users must log in (or register first user) before accessing features. All feature executions are logged and associated with the username.

- **Optional Encrypted Log Storage:** Before exiting you may encrypt the SQLite log database with a password. If encrypted, you will be prompted to decrypt on next launch; skipping creates a fresh empty log instead.

## Project Structure

The project structure is organized as follows:

```sh
DOTFORMAT/
├── src/
│   ├──__pycache__/
│   ├──images/                  # Image resources
│   │   ├──image.ico            # Shortcut icon for desktop (unfortunately you still have to do this manually)
│   │   └──image.png            # Image for the executable interface            
│   ├── models/                 # File conversion models
│   │   ├──__pycache__/
│   │   ├── __init__.py
│   │   ├── audio_to_text.py
│   │   ├── convert_image.py
│   │   ├── convert_video.py
│   │   ├── pdf_manager.py
│   │   ├── qrcode_generator.py
│   │   └── remove_background.py
│   └── gui.py                  # Graphical user interface
├── DOTformat.spec              # Project build specification file
├── LICENSE                     # Project license
├── main.py                     # Program entry point
├── README.md                   # Project documentation
├── requirements.txt            # List of required Python libraries
└── setup.py                    # Creates the virtual environment, installs all dependencies, and creates the .exe file
```

## Installation
Follow the steps below to set up the virtual environment, install the necessary dependencies, and create the executable file:

- Clone the repository:

```sh
git clone https://github.com/EdynuT/DOTformat.git
cd DOTformat
```

- In the terminal, type:

```sh
python setup.py
```

This way, the program should install without major issues.

Just a warning: when creating the executable, the log may get stuck with this message:

```sh
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
If youâ€™d like to contribute, please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write clear, concise commit messages.
4. Ensure that your code follows the existing style and is well commented.
5. Submit a pull request describing your changes and why theyâ€™re needed.

## License

MIT License

## Message

It is highly recommended to use DOTFORMAT version >=1.2.0 if you want to have access to the background remover and PDF password maker.

I will rarely make small bug fixes, but it may happen at some point.

## Security & Privacy

DOTformat stores only local data; no information is transmitted externally.

Authentication:
- Passwords are hashed with PBKDF2-HMAC-SHA256 (salt + iterations) and never stored in plaintext.
- The first run (with no users) opens directly in registration mode.

Logging:
- Every feature invocation is recorded with feature name, (optional) input/output paths, status, detail (truncated), timestamp, and username.
- The log aids troubleshooting and auditing on multi-user local machines.

Encryption (optional):
- On exit you may choose to encrypt the SQLite database (dotformat.db) into dotformat.db.dotf using AES (EAX mode) with a key derived via PBKDF2.
- Encrypted file format includes magic header, version, salt, nonce, tag, and ciphertext. Integrity and confidentiality are provided.
- Decryption occurs at startup if the encrypted file exists and you supply the correct password. If you cancel or fail, a new empty log will be initialized (the encrypted file remains).
- Keep your password safe—there is no recovery mechanism.

Threat Model Notes:
- This protects against casual/local inspection if the machine is shared, but does not mitigate malware or a user who has access while the app is running (since the DB must be plaintext during active use).
- Secure deletion attempts to overwrite the plaintext DB before removal, but on some filesystems remnants may still exist (typical limitation). For stronger guarantees use full-disk encryption.

## Data Storage Location

By default (non-portable builds) persistent files live in the OS user data directory (via platformdirs):

| Platform | Path Example |
|----------|--------------|
| Windows  | %LOCALAPPDATA%\DOTformat |
| macOS    | ~/Library/Application Support/DOTformat |
| Linux    | ~/.local/share/DOTformat |

Files stored there:
- `dotformat.db` (plaintext log during runtime)
- `dotformat.db.dotf` (encrypted form after exit if encryption enabled)
- `auth.db` (authentication + key wrappers)

Portable Mode:
- If environment variable `DOTFORMAT_PORTABLE=1` is set (or build invoked with `setup.py --portable`), databases are stored in a local `data/` directory alongside the executable.
- Useful for USB usage; remember this decreases host isolation (anyone with the stick can access the files if not encrypted).

Backups:
- To back up or migrate, copy the whole directory above (or `data/` in portable mode) while the application is closed.

## Portable Build

When running `python setup.py --portable`, the executable will expect to place/read databases inside a `data/` folder adjacent to the executable. Create this folder manually if you want to pre-populate with existing encrypted or plaintext DBs.

## Upgrading from 1.x

1. Remove any old conflicting virtual environment and recreate with Python 3.10.
2. Install dependencies from the cleaned requirements.txt.
3. Run the application; register initial user if prompted.
4. (Optional) Encrypt existing log on first exit if desired.

## Roadmap Ideas

- Pluggable export (CSV / JSON) for log history.
- Optional per-feature settings persistence.
- Graceful background removal dependency detection UI.
