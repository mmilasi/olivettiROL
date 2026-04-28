import os
import face_recognition
import numpy as np
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# 1. Connessione globale
client = MongoClient('mongodb://attendance_db:27017/')
db = client.get_database('attendance_system')

def init_db():
    db.users.delete_many({})
    db.lessons.delete_many({})
    db.presenze.delete_many({})
    print("--- 🔄 Database resettato con successo ---")

    # 2. Popolamento Docenti (per il login e la Dashboard)
    teachers = [
        {"username": "luca.martinelli", "full_name": "Luca Martinelli", "password": "password123", "materia": "Sistemi e Reti"},
        {"username": "stefano.castagnoli", "full_name": "Stefano Castagnoli", "password": "password123", "materia": "Architetture DevOps"},
        {"username": "davide.luppoli", "full_name": "Davide Luppoli", "password": "password123", "materia": "Cybersecurity"}
    ]
    
    for t in teachers:
        db.users.insert_one({
            "username": t['username'],
            "full_name": t['full_name'],
            "password": generate_password_hash(t['password']),
            "materia": t['materia'],
            "role": "teacher"
        })
    print(f"✅ {len(teachers)} Docenti creati.")

    # 3. Popolamento Studenti (per la simulazione del riconoscimento del Totem)
    # NOTA: Il 'filename' corrisponde al nome della foto che viene caricata nel Totem per lo scopo di simulazione senza uso di
    # tecnologie di riconoscimento facciale reali. In un caso reale, questa parte sarebbe gestita da un sistema di riconoscimento facciale.
    raw_students = [
            {"student_id": "S001", "name": "Giacomo Boni", "filename": "boni", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S002", "name": "Francesco Pucci Mamone", "filename": "pucci", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S003", "name": "Mattia Piovaccari", "filename": "piovaccari", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "attivo"}},
            {"student_id": "S004", "name": "Giacomo Venturi", "filename": "venturi", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S005", "name": "Michelangelo Ottaviani", "filename": "ottaviani", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "attivo"}},
            {"student_id": "S006", "name": "Enrico Fontana", "filename": "fontana", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "attivo"}},
            {"student_id": "S007", "name": "Samuele Angelicchio", "filename": "angelicchio", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S008", "name": "Nicolò Ramilli", "filename": "ramilli", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "attivo"}},
            {"student_id": "S009", "name": "Aminatou Pemboura", "filename": "pemboura", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S010", "name": "Giovanni Biancoli", "filename": "biancoli", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "attivo"}},
            {"student_id": "S011", "name": "Jean-Marie Gnando", "filename": "gnando", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S012", "name": "Davide Mineo", "filename": "mineo", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S013", "name": "Teodorina Lungu", "filename": "lungu", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S014", "name": "Marija Milasinovic", "filename": "milasinovic", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "no", "stato": "attivo"}},
            {"student_id": "S015", "name": "Gianni Esposito", "filename": "esposito", "metadata": {"corso": "Cloud DevOps 24/26", "fuorisede": "sì", "stato": "ritirato"}},
            {"student_id": "S016", "name": "Tizio Caio", "filename": "tizio", "metadata": {"corso": "Cybersecurity 24/26", "fuorisede": "sì", "stato": "attivo"}}
        ]

    for s in raw_students:
        name_parts = s['name'].split()
        nome = name_parts[0]
        cognome = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        # --- LOGICA AI: Estrazione lineamenti ---
        encoding = None
        path_img = f"img_students/{s['filename']}.jpg"
        
        if os.path.exists(path_img):
            image = face_recognition.load_image_file(path_img)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                encoding = encodings[0].tolist()
                print(f"🧬 AI: Lineamenti estratti per {s['name']}")
        
        db.users.insert_one({
            "username": s['filename'],
            "nome": nome,
            "cognome": cognome,
            "student_id": s['student_id'],
            "role": "student",
            "face_encoding": encoding,
            "metadata": s['metadata']
        })

    print(f"✅ Studenti registrati con successo (AI-ready).")

if __name__ == "__main__":
    init_db()