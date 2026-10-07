@echo off
setlocal
title OryvexClient Launcher
echo ==========================================
echo    OryvexClient  -  Minecraft 1.8.8
echo ==========================================
echo.

set "MC=%APPDATA%\.minecraft"
set "JAR=%~dp0OryvexClient.jar"
set "FORGE=1.8.8-11.15.0.1655"

if not exist "%JAR%" goto nojar
where java >nul 2>nul
if errorlevel 1 goto nojava
if not exist "%MC%" goto nomc

rem --- check that Forge 1.8.8 is installed ---
dir /b "%MC%\versions" 2>nul | findstr /i /r "1\.8\.8.*forge forge.*1\.8\.8" >nul
if not errorlevel 1 goto haveforge

echo Forge 1.8.8 was not found. Downloading the installer...
set "INST=%TEMP%\forge-%FORGE%-installer.jar"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://maven.minecraftforge.net/net/minecraftforge/forge/%FORGE%/forge-%FORGE%-installer.jar' -OutFile '%INST%'"
if not exist "%INST%" goto dlfail
echo In the installer window choose "Install client" and press OK.
java -jar "%INST%"

:haveforge
if not exist "%MC%\mods" mkdir "%MC%\mods"
copy /y "%JAR%" "%MC%\mods\OryvexClient.jar" >nul
echo OryvexClient installed to %MC%\mods
echo.

set "LAUNCHER="
if exist "%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe" set "LAUNCHER=%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe"
if exist "%ProgramFiles%\Minecraft Launcher\MinecraftLauncher.exe" set "LAUNCHER=%ProgramFiles%\Minecraft Launcher\MinecraftLauncher.exe"

if defined LAUNCHER (
    echo Starting the Minecraft Launcher. Select the profile named "forge" and press Play.
    start "" "%LAUNCHER%"
) else (
    echo Open your Minecraft Launcher and select the "forge" 1.8.8 profile.
)
echo In game: Right Shift = menu, C = zoom.
timeout /t 6 >nul
exit /b 0

:nojar
echo OryvexClient.jar was not found next to this file.
pause
exit /b 1
:nojava
echo Java was not found. Install Java 8 or newer and try again.
pause
exit /b 1
:nomc
echo .minecraft folder not found. Run the official Minecraft Launcher once first.
pause
exit /b 1
:dlfail
echo Could not download the Forge installer. Install Forge %FORGE% manually.
pause
exit /b 1
