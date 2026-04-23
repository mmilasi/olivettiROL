@echo off
setlocal enabledelayedexpansion
title ITS Attendance - Ultra Lazy Launcher

echo ============================================================
echo    VERIFICA REQUISITI DI SISTEMA (AUTO-INSTALLER)
echo ============================================================

:: 1. Verifica Permessi Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] ERRORE: Devi eseguire questo file come AMMINISTRATORE.
    echo Clicca col tasto destro sul file e seleziona "Esegui come amministratore".
    pause
    exit /b
)

:: 2. Controllo Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python non trovato. Installazione in corso...
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    echo [!] Python installato. Riavvia questo script per aggiornare i percorsi.
    pause
    exit /b
) else (
    echo [OK] Python rilevato.
)

:: 3. Controllo Docker Desktop
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker Desktop non trovato. Installazione in corso...
    echo (Questa operazione richiedera qualche minuto...)
    winget install -e --id Docker.DockerDesktop --silent --accept-package-agreements --accept-source-agreements
    echo [!] Docker installato. E necessario riavviare il PC per completare la configurazione.
    pause
    exit /b
) else (
    echo [OK] Docker rilevato.
)

:: 4. Verifica se Docker e acceso
docker info >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker e installato ma SPENTO. Avvio in corso...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo In attesa che Docker si carichi (puo metterci un minuto)...
    :wait_docker
    timeout /t 5 >nul
    docker info >nul 2>&1
    if %errorLevel% neq 0 goto wait_docker
    echo [OK] Docker e ora attivo.
)

echo ============================================================
echo    TUTTI I REQUISITI OK. AVVIO MICROSERVIZI...
echo ============================================================

echo [*] Costruzione container...
docker-compose up --build -d

echo [*] Installazione dipendenze Totem (PyQt6)...
pip install -r gui_client/requirements.txt --quiet

echo [*] Apertura Dashboard...
start http://localhost:5001/dashboard

echo [*] Lancio Totem...
python gui_client/app.py

echo ============================================================
echo    SISTEMA PRONTO! BUONA PRESENTAZIONE.
echo ============================================================
pause