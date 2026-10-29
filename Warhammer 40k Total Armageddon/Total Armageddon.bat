@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Falha ao instalar as dependencias necessarias para gerar o executavel.
    pause
    exit /b 1
)
python ferramentas\gerar_exe.py
if errorlevel 1 (
    echo.
    echo Falha ao gerar o executavel.
    pause
    exit /b 1
)
echo.
echo Abra: dist\Total Armageddon\Total Armageddon.exe
pause
