@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo ========================================
echo   元智選課機器人 - 本地打包腳本
echo ========================================
echo.

REM 檢查 Python 是否已安裝
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python！
    echo 請先安裝 Python 3.8 或以上版本
    echo 下載網址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 檢查 Python 版本...
python --version
echo.

REM 檢查 model.onnx 是否存在
if not exist "..\model.onnx" (
    echo [錯誤] 找不到 model.onnx 檔案！
    echo 請確保 model.onnx 在專案根目錄下
    pause
    exit /b 1
)

echo [2/4] 安裝必要套件...
pip install -r ..\requirements.txt
if %errorlevel% neq 0 (
    echo [錯誤] 套件安裝失敗！
    pause
    exit /b 1
)
echo.

echo [3/4] 使用 PyInstaller 打包程式...
pyinstaller yzuCourseBot.spec
if %errorlevel% neq 0 (
    echo [錯誤] 打包失敗！
    pause
    exit /b 1
)
echo.

echo [4/4] 檢查打包結果...
if exist "dist\元智選課機器人.exe" (
    echo.
    echo ========================================
    echo   打包成功！
    echo ========================================
    echo.
    echo 執行檔位置：dist\元智選課機器人.exe
    echo 檔案大小：
    dir "dist\元智選課機器人.exe" | find "元智選課機器人.exe"
    echo.
    echo 您可以將此檔案分享給其他人使用
    echo 執行檔無需安裝 Python 即可運行
    echo.
) else (
    echo [錯誤] 找不到打包後的執行檔！
    pause
    exit /b 1
)

echo 按任意鍵結束...
pause >nul

