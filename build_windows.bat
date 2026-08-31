@echo off
echo ============================================================
echo  Portfolio Manager — Build Windows
echo ============================================================
echo.

echo [1/4] Instalez dependintele Python...
python -m pip install flask requests beautifulsoup4 lxml yfinance pywebview pyinstaller google-auth-oauthlib

echo.
echo [2/4] Verific pywebview...
python -c "import webview; print('pywebview OK:', webview.__version__)" 2>nul || (
    echo ATENTIE: pywebview nu s-a instalat corect.
    echo Incearca: python -m pip install pywebview --upgrade
)

echo.
echo [3/4] Curat build-urile anterioare...
rmdir /s /q build 2>nul
rmdir /s /q dist  2>nul

echo.
echo [4/4] Construiesc executabilul...
python -m PyInstaller portfolio_manager.spec

echo.
echo ============================================================
if exist dist\PortfolioManager.exe (
    echo  SUCCES! Executabilul e in: dist\PortfolioManager.exe
    echo.
    echo  Poti copia PortfolioManager.exe oriunde vrei.
    echo  La prima rulare se creeaza portfolio_data.json langa .exe
    echo  Aplicatia se deschide intr-o fereastra proprie ^(fara browser^)
) else (
    echo  EROARE: executabilul nu a fost creat. Verifica mesajele de mai sus.
)
echo ============================================================
pause
