import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE MONGODB ---
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/attendance_system')
client = MongoClient(MONGO_URI)
db = client.get_database()

# --- ENDPOINT DI RILEVAMENTO PRESENZA ---
@app.route('/detect', methods=['POST'])
def detect():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H:%M:%S")

    # 1. VERIFICA SESSIONE ATTIVA
    lesson = db.lessons.find_one({"date": today, "is_active": True}, sort=[("_id", -1)])
    if not lesson:
        return jsonify({'message': 'SESSIONE TERMINATA: Il Totem è stato disattivato automaticamente'}), 403

    # 2. IDENTIFICAZIONE STUDENTE
    file = request.files.get('image')
    if not file: return jsonify({'message': 'Immagine mancante'}), 400
    
    filename_id = file.filename.split(".")[0].lower()
    student = db.users.find_one({"username": filename_id, "role": "student"})    
    if not student:
        return jsonify({'message': f'STUDENTE NON RICONOSCIUTO: {filename_id} non in anagrafica'}), 404

    full_name = f"{student['nome']} {student['cognome']}"

    # 3. LOGICA TOGGLE PRESENZA
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