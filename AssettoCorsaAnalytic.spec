# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Added files: frontend files, backend package, and .env
added_files = [
    ('frontend', 'frontend'),
    ('backend', 'backend'),
    ('.env', '.'),
]

a = Analysis(
    ['gui_launcher.py'], # Use the GUI launcher as the entry point
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'uvicorn.protocols.http.httptools_impl', 
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.wsproto_impl', 
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan.on', 
        'uvicorn.logging',
        'fastapi.middleware.cors',
        'email.mime.multipart',
        'email.mime.text',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='analisisAsseto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # HIDE TERMINAL WINDOW
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
