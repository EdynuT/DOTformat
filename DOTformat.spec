# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Base directory of the project
base_dir = os.path.abspath(os.getcwd())
src_dir = os.path.join(base_dir, 'src')

"""PyInstaller spec for DOTformat.

Fixed: Previously iterated over the string 'requirements.txt' which caused
PyInstaller to attempt collecting single characters as modules. Now we
explicitly (and defensively) collect a curated set of libraries if present.

Optional heavy packages (e.g. rembg) are wrapped in try/except so missing
ones won't break the build; the GUI handles absence with lazy imports.
"""

# Curated import names to try collecting. Only those actually installed will
# contribute resources; failures are silently ignored to keep build robust.
candidate_libs = [
    'ffmpeg',              # from ffmpeg-python
    'PIL',                 # pillow
    'PyPDF2',
    'pdf2docx',
    'pdf2image',
    'fitz',                # PyMuPDF
    'qrcode',
    'pydub',
    'speech_recognition',
    'img2pdf',
    'pikepdf',
    'rembg',               # optional - may be absent
]

datas = []
binaries = []
hiddenimports = []

for lib in candidate_libs:
    try:
        collected = collect_all(lib)
        datas += collected[0]
        binaries += collected[1]
        hiddenimports += collected[2]
    except Exception:
        # Library not installed or failed to collect; skip.
        pass

# Project-specific data: includes the GUI image, conversion scripts, and ffmpeg.exe (if needed)
if os.path.exists(os.path.join(src_dir, 'images', 'image.png')):
    datas.append((os.path.join(src_dir, 'images', 'image.png'), 'images'))

if os.path.exists(os.path.join(src_dir, 'models')):
    datas.append((os.path.join(src_dir, 'models'), 'models'))

ffmpeg_exe = os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')
if os.path.exists(ffmpeg_exe):
    datas.append((ffmpeg_exe, os.path.join('ffmpeg', 'bin')))

a = Analysis(
    [os.path.join(base_dir, 'main.py')],
    pathex=[base_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DOTformat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(src_dir, 'images', 'image.ico') if os.path.exists(os.path.join(src_dir, 'images', 'image.ico')) else None
)