@echo off
title CloudLab Intel - Student Workstation Agent
color 0A
echo ========================================================
echo   Starting CloudLab Intel Student Workstation Agent...
echo ========================================================
if exist CloudLabAgent.exe (
    start CloudLabAgent.exe
) else (
    python client_agent_gui.py
)
