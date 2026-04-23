@echo off
setlocal enabledelayedexpansion
title ITS Attendance - Lazy Launcher

cd /d "%~dp0"

echo ============================================================
echo    VERIFICA REQUISITI DI SISTEMA
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
    echo [!] Python non trovato. Provo a installarlo...
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements
    echo [!] Riavvia lo script dopo l'installazione.
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
    echo [!] Docker Desktop non trovato. Installazione in corso...
    winget install -e --id Docker.DockerDesktop --silent --accept-package-agreements
    echo [!] Docker installato. E' NECESSARIO RIAVVIARE IL PC.
    pause
    exit /b
) else (
    echo [OK] Docker rilevato.
)

:: 4. Verifica se Docker e ACCESO
echo [*] Verifica stato servizio Docker...
docker info >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker e SPENTO. Lo avvio per te...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Attendo che il motore di Docker sia pronto...
    :wait_docker
    timeout /t 5 >nul
    docker info >nul 2>&1
    if %errorLevel% neq 0 (
        set /a retry+=1
        if !retry! gtr 20 (
            echo [!] Docker ci mette troppo. Aprilo a mano.
            pause
            exit /b
        )
        goto wait_docker
    )
    echo [OK] Docker e operativo.
)

echo ============================================================
echo    LANCIO PROGETTO DA: %cd%
echo ============================================================

:: Avvio Docker Compose
docker-compose up --build -d

:: Installazione dipendenze Totem
echo [*] Installazione librerie Totem...
pip install -r gui_client/requirements.txt --quiet

:: Apertura Dashboard
echo [*] Apertura Dashboard...
start http://localhost:5001/dashboard

:: Avvio Totem
echo [*] Lancio Totem GUI...
python gui_client/app.py

echo ============================================================
echo    SISTEMA PRONTO!
echo ============================================================
pause