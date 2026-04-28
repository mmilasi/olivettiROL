import os
import datetime
import face_recognition
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# Configurazione MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/attendance_system')
client = MongoClient(MONGO_URI)
db = client.get_database()

@app.route('/detect', methods=['POST'])
def detect():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H:%M:%S")

    # 1. VERIFICA SESSIONE ATTIVA
    lesson = db.lessons.find_one({"date": today, "is_active": True}, sort=[("_id", -1)])
    if not lesson:
        return jsonify({'message': 'SESSIONE TERMINATA: Il Totem è stato disattivato automaticamente'}), 403

    # 2. RICEZIONE IMMAGINE
    file = request.files.get('image')
    if not file: 
        return jsonify({'message': 'Immagine mancante'}), 400
    
    try:
        unknown_image = face_recognition.load_image_file(file)
        unknown_encodings = face_recognition.face_encodings(unknown_image)
    except Exception as e:
        return jsonify({'message': f'Errore processamento immagine: {str(e)}'}), 500

    if not unknown_encodings:
        return jsonify({'message': 'Nessun volto rilevato nell\'immagine'}), 400

    current_face_encoding = unknown_encodings[0]

    # 3. CONFRONTO AI
    # Recuperiamo tutti gli studenti che hanno un profilo biometrico salvato
    students = list(db.users.find({"role": "student", "face_encoding": {"$ne": None}}))
    
    if not students:
        return jsonify({'message': 'Anagrafica biometrica vuota'}), 404

    # Creiamo la lista dei vettori noti
    known_encodings = [np.array(s['face_encoding']) for s in students]

    # L'AI confronta i volti: restituisce una lista di True/False
    results = face_recognition.compare_faces(known_encodings, current_face_encoding, tolerance=0.6)

    if True in results:
        match_index = results.index(True)
        student = students[match_index]
        filename_id = student['username']
        full_name = f"{student['nome']} {student['cognome']}"
    else:
        return jsonify({'message': 'STUDENTE NON RICONOSCIUTO: Studente non presente in anagrafica'}), 404

    # 4. LOGICA TOGGLE PRESENZA
    presence = db.presenze.find_one({"username": filename_id, "date": today, "exit_time": None})
    
    if presence:
        db.presenze.update_one({"_id": presence["_id"]}, {"$set": {"exit_time": timestamp, "status": "Uscito"}})
        return jsonify({"message": f"Arrivederci {full_name}"}), 200
    else:
        db.presenze.insert_one({
            "username": filename_id, "student_name": full_name, "date": today,
            "entry_time": timestamp, "exit_time": None, "status": "Presente",
            "teacher": lesson['teacher'], "lesson": lesson['description']
        })
        return jsonify({"message": f"Benvenuto {full_name}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)