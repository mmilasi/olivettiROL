import os
import datetime
import jwt
from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient(os.getenv('MONGO_URI'))
db = client.get_database()

@app.route('/detect', methods=['POST'])
def detect():
    # token verification
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'message': 'Token mancante o formato errato'}), 401
    
    token = auth_header.split(" ")[1]

    try:
        user_info = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token scaduto'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Token non valido'}), 401

    # get image
    file = request.files.get('image')

    if file and file.filename:
        student_name = file.filename.split(".")[0]
    else:
        return jsonify({'message': 'Immagine mancante'}), 400

    # log attendance
    presenza = {
        "studente": student_name,
        "data": datetime.datetime.now(),
        "docente_che_ha_scansionato": user_info['username']
    }
    db.presenze.insert_one(presenza)

    return jsonify({"message": f"Presenza registrata per {student_name}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)