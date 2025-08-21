@echo off
echo ========================================
echo   VPN Monitoring System
echo ========================================
echo.

echo Backend baslatiliyor...
echo.

REM Python sanal ortamını aktifleştir
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Python sanal ortami aktiflestirildi
) else (
    echo Python sanal ortami bulunamadi
    echo Lutfen once 'python -m venv venv' komutunu calistirin
    pause
    exit /b 1
)

REM Backend'i başlat
echo Backend baslatiliyor...
start "Backend" cmd /k "python start_backend.py"

echo.
echo Backend baslatildi. Tarayicida http://localhost:8000 adresini ziyaret edin
echo.

REM Frontend'i başlat
echo Frontend baslatiliyor...
cd frontend
start "Frontend" cmd /k "npm start"

echo.
echo ========================================
echo   Uygulama baslatildi!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Uygulamayi durdurmak icin her iki pencereyi de kapatın.
echo.
pause
