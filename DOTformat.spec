# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Diretório base do projeto
base_dir = os.path.abspath(os.getcwd())
src_dir = os.path.join(base_dir, 'src')

# Lista de bibliotecas (nome de import, quando necessário, ajuste para o nome correto)
# Note que algumas bibliotecas são instaladas com um nome e importadas com outro:
# ex.: "ffmpeg-python" é importado como "ffmpeg", "pillow" como "PIL", "python-docx" como "docx", 
#       "PyMuPDF" como "fitz", "SpeechRecognition" como "speech_recognition", etc.
libraries = [
    'altgraph',
    'cffi',
    'chardet',
    'colorama',
    'decorator',
    'Deprecated',
    'ffmpeg-python',
    'fire',
    'fonttools',
    'future',
    'imageio',
    'imageio-ffmpeg',
    'img2pdf',
    'lxml',
    'moviepy',
    'numpy',
    'opencv-python-headless',
    'packaging',
    'pdf2docx',
    'pdf2image',
    'pefile',
    'pikepdf',
    'pillow',
    'proglog',
    'pycparser',
    'pydub',
    'pyinstaller',
    'pyinstaller-hooks-contrib',
    'PyMuPDF',
    'PyPDF2',
    'python-docx',
    'python-dotenv',
    'pywin32-ctypes',
    'qrcode',
    'reportlab',
    'setuptools',
    'SpeechRecognition',
    'termcolor',
    'tqdm',
    'typing_extensions',
    'wrapt'
]

datas = []
binaries = []
hiddenimports = []

# Coleta recursos (dados, binários e hiddenimports) de cada biblioteca
for lib in libraries:
    collected = collect_all(lib)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]

# Dados específicos do projeto: inclui a imagem do GUI, os scripts de conversão e o ffmpeg.exe (se necessário)
datas += [
    (os.path.join(src_dir, 'images', 'image.png'), 'images'),
    (os.path.join(src_dir, 'conversores'), 'conversores'),
    (os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe'), os.path.join('ffmpeg', 'bin')),
]

a = Analysis(
    [os.path.join(src_dir, 'gui.py')],
    pathex=[src_dir],
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
    console=False
)