# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — ONEFILE mode (only one .exe)

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('index.html', '.')],
    hiddenimports=[
        'flask', 'flask.json', 'werkzeug',
        'requests', 'bs4', 'lxml', 'yfinance',
        'curl_cffi',
        'google.auth', 'google.auth.transport.requests',
        'google.oauth2.credentials', 'google_auth_oauthlib.flow',
        'google.auth.exceptions', 'google.oauth2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='PortfolioManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
