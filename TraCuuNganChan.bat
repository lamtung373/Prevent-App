@echo off
REM File batch đơn giản - chỉ gọi Python main.py
REM Toàn bộ logic đã được chuyển sang app/main.py để hỗ trợ log tiếng Việt có dấu

title Tra Cuu Tu Dong
color 0A

REM Lấy đường dẫn thư mục gốc (file batch đang ở thư mục gốc)
set "PROJECT_ROOT=%~dp0"
set "APP_DIR=%PROJECT_ROOT%app"
set "MAIN_SCRIPT=%APP_DIR%\main.py"

REM Kiểm tra Python cơ bản
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat!
    echo Vui long cai tai: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Kiểm tra file main.py
if not exist "%MAIN_SCRIPT%" (
    echo [LOI] Khong tim thay file main.py: %MAIN_SCRIPT%
    pause
    exit /b 1
)

REM Chạy Python main.py
python "%MAIN_SCRIPT%"

REM Giữ exit code từ Python
set "EXITCODE=%errorlevel%"
exit /b %EXITCODE%