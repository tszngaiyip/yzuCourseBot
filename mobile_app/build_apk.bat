@echo off
setlocal enabledelayedexpansion

echo =========================================
echo  Starting WSL to run Buildozer APK Build
echo =========================================
echo.

:: Check if WSL is available
where wsl >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] WSL (Windows Subsystem for Linux) is not installed or not in PATH.
    echo Please install WSL first.
    pause
    exit /b 1
)

:: Check if buildozer is installed in WSL
wsl bash -c "[ -f ~/.local/bin/buildozer ]"
if %errorlevel% neq 0 (
    echo Buildozer was not detected in WSL.
    set /p install_choice="Would you like to install Buildozer and its dependencies now? (Y/N): "
    if /i "!install_choice!"=="Y" (
        echo.
        echo Installing dependencies (may prompt for WSL sudo password)...
        wsl bash -c "sudo apt update && sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev libtinfo6 cmake libffi-dev libssl-dev"
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install apt dependencies.
            pause
            exit /b !errorlevel!
        )
        
        echo.
        echo Installing Buildozer via pip3...
        wsl bash -c "pip3 install --user --upgrade Cython virtualenv buildozer --break-system-packages"
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install buildozer via pip.
            pause
            exit /b !errorlevel!
        )
        echo.
        echo =========================================
        echo  Buildozer installation successful!
        echo =========================================
        echo.
    ) else (
        echo.
        echo Skipping installation. Attempting to build anyway...
    )
)

echo.
echo NOTE: This process might take a long time.
echo.

wsl bash -l -c "export PIP_BREAK_SYSTEM_PACKAGES=1 && cd \"$(wslpath -u '%cd%')\" && ~/.local/bin/buildozer android debug"

echo.
echo =========================================
echo  Build process finished.
echo  If successful, APK will be in bin/ folder.
echo =========================================
pause
