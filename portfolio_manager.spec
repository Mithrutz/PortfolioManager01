# portfolio_manager.spec
# Rulare: python -m PyInstaller portfolio_manager.spec

from PyInstaller.building.build_main import Analysis, PYZ, EXE

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[('index.html', '.')],
    hiddenimports=[
        # Flask
        'flask', 'werkzeug', 'werkzeug.serving', 'werkzeug.utils',
        'jinja2', 'click',
        # Requests / scraping
        'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna',
        'bs4', 'lxml', 'lxml.etree', 'lxml.html',
        # yfinance si dependinte
        'yfinance', 'pandas', 'numpy', 'multitasking', 'frozendict',
        'requests_cache', 'platformdirs', 'curl_cffi',
        'peewee', 'appdirs',
        # pywebview — Windows foloseste EdgeChromium (WebView2)
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.platforms.cef',
        'clr',        # pythonnet pentru WinForms
        'System',
        'System.Windows.Forms',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'PIL', 'tkinter', 'PyQt5', 'PyQt6'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PortfolioManager',
    debug=False,
    strip=False,
    upx=True,
    console=False,    # fara fereastra Command Prompt
    icon=None,
)
