# ROL - Registro OffLine - ITS Academy Olivetti


Sistema biometrico intelligente per la gestione delle presenze, basato su microservizi e Intelligenza Artificiale.

## 🚀 Avvio Rapido (Consigliato)
Se sei su Windows, puoi avviare l'intero progetto (inclusa l'installazione dei prerequisiti) semplicemente eseguendo:
1. Tasto destro su `avvioProgetto.bat`
2. Seleziona **"Esegui come amministratore"**

Lo script installerà Python e Docker Desktop se non presenti, configurerà Docker, installerà le librerie necessarie e aprirà automaticamente Dashboard e Totem. 
In caso di installazione di Python o Docker sarà neccessario riavviare il .bat (sempre come amministratore).

---

## 🛠️ Architettura e Tecnologie
- **Backend**: Flask (Python) in configurazione Microservizi.
- **AI Engine**: Dlib & Face_Recognition (DNA Digitale a 128 dimensioni).
- **Database**: MongoDB (NoSQL).
- **DevOps**: Docker, Docker-Compose, Batch Scripting.
- **Security**: Autenticazione JWT e hashing delle password con Werkzeug.

## 📂 Struttura del Progetto
- `/auth_service`: Gestione utenti, login JWT e generazione report PDF.
- `/detection_service`: Motore di Intelligenza Artificiale per il riconoscimento facciale.
- `/gui_client`: Interfaccia Totem hardware-simulated (PyQt6).
- `/img_students`: Database fisico delle immagini per il training AI.

## ⚙️ Installazione Manuale (Alternative)
Se preferisci non usare il launcher automatico:
1. `docker-compose up --build -d`
2. `docker exec -it auth_microservice python init_db.py` (Per popolare l'anagrafica biometrica)
3. Apri `http://localhost:5001/dashboard`
4. Esegui localmente `python gui_client/app.py`

## 👩🏻‍💻 Sviluppato da
Marija Milasinovic
Corso: Cloud DevOps 24/26 - ITS Academy Olivetti - Cesena