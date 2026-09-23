@echo off
title CloudLab Intel - Open Windows Firewall for Lab LAN
color 0A
echo ======================================================================
echo    OPENING WINDOWS FIREWALL FOR STUDENT CONNECTIONS (PORT 5000, 5001)
echo ======================================================================
echo.
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [*] Adding Inbound Rule for Port 5000 (Cloud Analytics)...
netsh advfirewall firewall delete rule name="CloudLab Port 5000" >nul 2>&1
netsh advfirewall firewall add rule name="CloudLab Port 5000" dir=in action=allow protocol=TCP localport=5000 profile=any >nul 2>&1

echo [*] Adding Inbound Rule for Port 5001 (Edge Node Server)...
netsh advfirewall firewall delete rule name="CloudLab Port 5001" >nul 2>&1
netsh advfirewall firewall add rule name="CloudLab Port 5001" dir=in action=allow protocol=TCP localport=5001 profile=any >nul 2>&1

echo.
echo [SUCCESS] Windows Firewall is now OPEN for Student PCs to connect!
echo [*] Students can now connect seamlessly via Port 5001.
echo.
pause
