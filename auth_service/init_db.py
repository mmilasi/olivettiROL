import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Connessione globale
client = MongoClient('mongodb://localhost:27017/')
db = client.get_database('attendance_system')

def init_db():
    # 1. Reset totale delle collezioni per evitare duplicati o conflitti
    db.users.delete_many({})
    db.students.delete_many({})
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
        t['password'] = generate_password_hash(t['password'])
        t['role'] = 'teacher'
        db.users.insert_one(t)
    print(f"✅ {len(teachers)} Docenti creati.")

    # 3. Popolamento Studenti (per la simulazione del riconoscimento del Totem)
    # NOTA: Il 'filename' corrisponde al nome della foto che viene caricata nel Totem per lo scopo di simulazione senza uso di
    # tecnologie di riconoscimento facciale reali. In un caso reale, questa parte sarebbe gestita da un sistema di riconoscimento facciale.
    students = [
        {"student_id": "S001", "name": "Giacomo Boni", "filename": "boni"},
        {"student_id": "S002", "name": "Francesco Pucci Mamone", "filename": "pucci"},
        {"student_id": "S003", "name": "Mattia Piovaccari", "filename": "piovaccari"},
        {"student_id": "S004", "name": "Giacomo Venturi", "filename": "venturi"},
        {"student_id": "S005", "name": "Michelangelo Ottaviani", "filename": "ottaviani"},
        {"student_id": "S006", "name": "Enrico Fontana", "filename": "fontana"},
        {"student_id": "S007", "name": "Samuele Angelicchio", "filename": "angelicchio"},
        {"student_id": "S008", "name": "Nicolò Ramilli", "filename": "ramilli"},
        {"student_id": "S009", "name": "Aminatou Pemboura", "filename": "pemboura"},
        {"student_id": "S010", "name": "Giovanni Biancoli", "filename": "biancoli"},
        {"student_id": "S011", "name": "Jean-Marie Gnando", "filename": "gnando"},
        {"student_id": "S012", "name": "Davide Mineo", "filename": "mineo"},
        {"student_id": "S013", "name": "Teodorina Lungu", "filename": "Lungu"},
        {"student_id": "S014", "name": "Marija Milasinovic", "filename": "milasinovic"}
    ]
    db.students.insert_many(students)
    print(f"✅ {len(students)} Studenti registrati nell'anagrafica.")

if __name__ == "__main__":
    init_db()