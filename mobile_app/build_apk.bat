@echo off
echo =========================================
echo  Starting WSL to run Buildozer APK Build
echo =========================================
echo.
echo NOTE: This process might take a long time.
echo Please ensure buildozer is installed in WSL.
echo.

wsl bash -l -c "export PIP_BREAK_SYSTEM_PACKAGES=1 && cd \"$(wslpath -u '%cd%')\" && ~/.local/bin/buildozer android debug"

echo.
echo =========================================
echo  Build process finished.
echo  If successful, APK will be in bin/ folder.
echo =========================================
pause
