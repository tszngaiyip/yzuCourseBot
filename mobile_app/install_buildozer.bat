@echo off
echo =========================================
echo  Installing Buildozer and dependencies in WSL
echo =========================================
echo This may prompt you for your WSL (Linux) sudo password.
echo.

wsl bash -c "sudo apt update && sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev libtinfo6 cmake libffi-dev libssl-dev"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install apt dependencies.
    pause
    exit /b %errorlevel%
)

echo.
echo Installing Buildozer via pip3...
wsl bash -c "pip3 install --user --upgrade Cython virtualenv buildozer --break-system-packages"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install buildozer via pip.
    pause
    exit /b %errorlevel%
)

echo.
echo =========================================
echo  Buildozer installation successful!
echo =========================================
pause
