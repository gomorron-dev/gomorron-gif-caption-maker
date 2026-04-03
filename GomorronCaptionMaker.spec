# -*- mode: python ; coding: utf-8 -*-
# GomorronCaptionMaker.spec
# Run with: pyinstaller GomorronCaptionMaker.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys, os

block_cipher = None

# Collect PIL/Pillow data
datas = collect_data_files('PIL')

# Add your icon and font files if present next to this spec
extra_datas = []
for f in ['icon.ico', 'icon.jpg', 'Impact.ttf', 'impact.ttf']:
    if os.path.isfile(f):
        extra_datas.append((f, '.'))

datas += extra_datas

# Bundle ffmpeg/ffprobe binaries if present next to this spec
# NOTE: ffmpeg is NOT bundled — the app downloads it automatically on first video use.
extra_binaries = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.ImageSequence',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'imageio_ffmpeg',
        'shutil',
        'subprocess',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy',
        'PyQt5', 'PyQt6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name='GomorronCaptionMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No console window
    icon='icon.ico' if os.path.isfile('icon.ico') else None,
    version_file=None,
)
