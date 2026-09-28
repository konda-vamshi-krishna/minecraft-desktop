@echo off
title Minecraft Desktop (Universal 1-Click Edition)
cd /d "%~dp0"

if exist "%~dp0minecraft.exe" (
    start "" "%~dp0minecraft.exe"
    exit /b 0
)

if exist "%~dp0build\minecraft.exe" (
    start "" "%~dp0build\minecraft.exe"
    exit /b 0
)

if exist "%~dp0dist\minecraft-desktop\minecraft.exe" (
    start "" "%~dp0dist\minecraft-desktop\minecraft.exe"
    exit /b 0
)

if exist "%~dp0game\minecraft-desktop\minecraft.exe" (
    start "" "%~dp0game\minecraft-desktop\minecraft.exe"
    exit /b 0
)

echo [ERROR] minecraft.exe not found! Please build the game or extract the release package.
pause
exit /b 1
