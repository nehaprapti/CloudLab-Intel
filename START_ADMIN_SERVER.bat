@echo off
title CloudLab Intel - Master Server Launcher
color 0B
echo ======================================================================
echo    CLOUDLAB INTEL: OFFLINE-FIRST EDGE-CLOUD PLATFORM
echo    SONA COLLEGE OF TECHNOLOGY - DEPT OF IT (BATCH 10)
echo ======================================================================
echo.
echo [*] Finding Local LAN IPv4 Address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    echo [LAN IP] %%a
)
echo.
echo [*] Starting Cloud and Edge Servers on Port 5000 and 5001...
echo [*] Open Browser at: http://localhost:5000
echo.
where python >nul 2>nul
if %errorlevel% equ 0 (
    python run_system.py
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        py run_system.py
    ) else (
        if exist "CloudLabServer.exe" (
            CloudLabServer.exe
        ) else (
            echo [ERROR] Neither Python nor CloudLabServer.exe was found.
        )
    )
)
pause
