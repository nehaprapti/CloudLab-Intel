@echo off
title CloudLab Intel - Authorized Admin Security Vault
color 0B
echo ======================================================================
echo    CLOUDLAB INTEL: SECURE AUTHORIZED ADMIN VAULT MANAGER
echo    SONA COLLEGE OF TECHNOLOGY - DEPT OF IT (BATCH 10)
echo ======================================================================
echo.
echo [*] Launching Master Admin Security Vault...
echo.
where python >nul 2>nul
if %errorlevel% equ 0 (
    python manage_admins.py
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        py manage_admins.py
    ) else (
        echo [ERROR] Python environment was not found. Please install Python.
        pause
    )
)
