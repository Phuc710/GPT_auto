@echo off
chcp 65001 >nul 2>&1
title GPT Auto Register - Setup

echo.
echo ══════════════════════════════════════════════════════════════
echo   GPT AUTO REGISTER - SETUP TỰ ĐỘNG
echo ══════════════════════════════════════════════════════════════
echo.

REM ── 1. Python ───────────────────────────────
echo [1/4] Kiểm tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python chưa được cài.
    echo     Mở trang download Python...
    start https://www.python.org/downloads/
    echo.
    echo     Cài Python xong rồi nhấn Enter để tiếp tục...
    pause >nul
)
for /f "tokens=*" %%i in ('python --version 2^>&1') do echo [OK] %%i
echo.

REM ── 2. Pip packages ─────────────────────────
echo [2/4] Cài thư viện Python (requirements.txt)...
python -m pip install --upgrade pip --quiet 2>nul
python -m pip install -r "%~dp0requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo [!] Lỗi cài thư viện. Chạy lại có thể fix...
    python -m pip install -r "%~dp0requirements.txt"
    pause
    exit /b 1
)
echo [OK] Tất cả thư viện đã được cài.
echo.

REM ── 3. Brave Browser ────────────────────────
echo [3/4] Kiểm tra Brave Browser...
set BRAVE_1=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
set BRAVE_2=C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe
set "BRAVE_3=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"

set BRAVE_FOUND=0
if exist "%BRAVE_1%" set BRAVE_FOUND=1
if exist "%BRAVE_2%" set BRAVE_FOUND=1
if exist "%BRAVE_3%" set BRAVE_FOUND=1

if %BRAVE_FOUND%==1 (
    echo [OK] Brave Browser đã được cài.
) else (
    echo [!] Chưa tìm thấy Brave Browser.
    echo     Mở trang download Brave...
    start https://brave.com/download/
    echo.
    echo     Cài Brave xong rồi nhấn Enter để tiếp tục...
    pause >nul
)
echo.

REM ── 4. File .env ─────────────────────────────
echo [4/4] Kiểm tra file .env...
if not exist "%~dp0.env" (
    echo [!] Chưa có file .env
    echo     Tạo file .env mẫu từ .env.example...
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env" >nul
        echo [OK] Đã tạo .env từ .env.example
        echo.
        echo     *** QUAN TRỌNG ***
        echo     Mở file .env và điền KAIMAIL_API_KEY và KAIMAIL_SECRET_KEY vào!
        echo     Bất kỳ editor nào cũng được (Notepad, VS Code...)
        echo.
        start notepad "%~dp0.env"
        echo     Điền key xong rồi nhấn Enter...
        pause >nul
    ) else (
        echo [!] Không tìm thấy .env.example
    )
) else (
    echo [OK] File .env đã tồn tại.
)
echo.

REM ── Tạo thư mục ──────────────────────────────
if not exist "%~dp0infoacc" mkdir "%~dp0infoacc"
if not exist "%~dp0.browser_profiles" mkdir "%~dp0.browser_profiles"

REM ── Xong ─────────────────────────────────────
echo ══════════════════════════════════════════════════════════════
echo   SETUP HOÀN TẤT!
echo ══════════════════════════════════════════════════════════════
echo.
echo Lưu ý:
echo   - Nếu bị Cloudflare, bật VPN chọn US (United States)
echo   - Đảm bảo đã điền API key vào file .env
echo   - Chạy: python main.py
echo.
echo Chạy main.py ngay bây giờ? Nhấn Enter = có, nhấn X = thoát...
set /p RUN_NOW="> "
if /i "%RUN_NOW%"=="x" goto :EOF
if /i "%RUN_NOW%"=="X" goto :EOF
cd /d "%~dp0"
python main.py
