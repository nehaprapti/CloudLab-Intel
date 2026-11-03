@echo off
title CloudLab Intelligence - Student Workstation Agent
color 0B
cls
echo ======================================================================
echo    CLOUDLAB INTELLIGENCE : STUDENT WORKSTATION AGENT
echo    SONA COLLEGE OF TECHNOLOGY - DEPT OF IT (BATCH 10)
echo ======================================================================
echo.
echo  [*] Initializing Student Agent Workstation Interface...
echo  [*] Two-Factor Email OTP Workstation Security Enforced.
echo.
where python >nul 2>nul
if %errorlevel% equ 0 (
    python client_agent_gui.py
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        py client_agent_gui.py
    ) else (
        if exist CloudLabAgent.exe (
            start CloudLabAgent.exe
        ) else (
            echo [ERROR] Neither Python nor CloudLabAgent.exe was found.
            pause
        )
    )
)
