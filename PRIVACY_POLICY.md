# Privacy Policy

Last updated: 2025-10-25

DOTformat is a desktop application that runs locally on your computer. We value your privacy and designed the app to minimize data collection.

## What the app stores locally
- Conversion history ("logs"): feature name, time, status (success/error), brief detail, and input/output file paths.
- Authentication data: usernames and password hashes (no plaintext). If you enable at-exit encryption, the database is encrypted on close.

## What is sent over the network
- By default, DOTformat does not send telemetry.
- Audio → Text uses Google Web Speech API for speech recognition. During transcription, audio chunks are sent to Google’s service for processing. The app does not retain those audio chunks after the operation finishes.
- Optional FFmpeg download: if FFmpeg is not found, the app may offer a guided download from a trusted source. This downloads the binary to your user data directory.

## Your controls
- Export my data: you can export your logs to CSV.
- Delete my data: you can delete your logs stored locally for your user.
- Encryption: you can protect the local database on app close using a password.

## Data retention
- Logs remain on your device until you delete them or uninstall the app. The app keeps at most the last N backups of the database when enabled.

## Third‑party components
- FFmpeg (binaries) — subject to their licenses.
- PyMuPDF, SpeechRecognition, pydub, Pillow, and other open‑source libraries — see project [LICENSE](./LICENSE) and respective licenses.

## Contact
If you have questions or requests, open an issue on the GitHub repository.
