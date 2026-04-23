@echo off
setlocal enabledelayedexpansion
title ITS Attendance - Lazy Launcher

cd /d "%~dp0"

echo ============================================================
echo     VERIFICA REQUISITI DI SISTEMA
echo ============================================================

:: 1. Verifica Permessi Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] ERRORE: Devi eseguire questo file come AMMINISTRATORE.
    echo Clicca col tasto destro e seleziona "Esegui come amministratore".
    pause
    exit /b
)

:: 2. Controllo Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python non trovato. Inizio installazione...
    where winget >nul 2>&1
    if %errorLevel% == 0 (
        echo [*] Utilizzo di winget per Python...
        winget install -e --id Python.Python.3.11 --silent --accept-package-agreements
    ) else (
        echo [!] winget non trovato. Scaricamento manuale via curl...
        curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
        echo [*] Esecuzione installer Python...
        start /wait "" "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1
    )
    echo [!] Riavvia lo script dopo l'installazione di Python.
    pause
    exit /b
) else (
    echo [OK] Python rilevato.
)

:: 3. Controllo Docker
set DOCKER_FOUND=0
docker --version >nul 2>&1 && set DOCKER_FOUND=1
if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" set DOCKER_FOUND=1

if !DOCKER_FOUND! equ 0 (
    echo [!] Docker Desktop non trovato. Inizio installazione...
    where winget >nul 2>&1
    if %errorLevel% == 0 (
        echo [*] Utilizzo di winget per Docker...
        winget install -e --id Docker.DockerDesktop --silent --accept-package-agreements
    ) else (
        echo [!] winget non trovato. Scaricamento manuale via curl...
        :: Nota: il doppio %% serve per gestire l'URL correttamente nel file .bat
        curl -L -o "%TEMP%\DockerInstaller.exe" "https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe"
        echo [*] Esecuzione installer Docker...
        start /wait "" "%TEMP%\DockerInstaller.exe"
    )
    echo [!] Docker installato. E' NECESSARIO RIAVVIARE IL PC.
    pause
    exit /b
) else (
    echo [OK] Docker rilevato.
)

:: 4. Verifica se Docker è ACCESO
echo [*] Verifica stato servizio Docker...
docker info >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker è SPENTO. Lo avvio per te...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [!] Impossibile trovare l'eseguibile di Docker Desktop. Aprilo manualmente.
        pause
        exit /b
    )
    
    echo Attendo che il motore di Docker sia pronto...
    set retry=0
    :wait_docker
    timeout /t 5 >nul
    docker info >nul 2>&1
    if %errorLevel% neq 0 (
        set /a retry+=1
        if !retry! gtr 20 (
            echo [!] Docker ci mette troppo. Aprilo a mano e riavvia lo script.
            pause
            exit /b
        )
        goto wait_docker
    )
    echo [OK] Docker è operativo.
)

echo ============================================================
echo     LANCIO PROGETTO DA: %cd%
echo ============================================================

:: Avvio Docker Compose
docker-compose up --build -d

:: Installazione dipendenze Totem
echo [*] Installazione librerie Totem...
python -m pip install --upgrade pip --quiet --no-warn-script-location
python -m pip install -r gui_client/requirements.txt --quiet --no-warn-script-location

:: Apertura Dashboard
echo [*] Apertura Dashboard...
start http://localhost:5001/dashboard

:: Avvio Totem
echo [*] Lancio Totem GUI...
python gui_client/app.py

echo ============================================================
echo     SISTEMA PRONTO!
echo ============================================================
pause