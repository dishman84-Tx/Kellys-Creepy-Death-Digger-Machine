@echo off
echo ========================================================
echo Building Kelly's Creepy Death Digger Machine v1.3
echo ========================================================

REM Clean previous builds
if exist build rd /s /q build
if exist dist rd /s /q dist

REM Run PyInstaller
REM --icon: Sets the EXE file icon
python -m PyInstaller --noconsole ^
    --name "KellysCreepyDeathDigger" ^
    --icon "ui/assets/icon.ico" ^
    --add-data "ui/assets;ui/assets" ^
    --add-data "database;database" ^
    --add-data "credentials;credentials" ^
    --add-data "export;export" ^
    --hidden-import PyQt6.QtMultimedia ^
    --hidden-import PyQt6.QtMultimediaWidgets ^
    --collect-all nodriver ^
    main.py

echo.
echo ========================================================
echo Build Complete! Check the 'dist' folder.
echo ========================================================
pause
