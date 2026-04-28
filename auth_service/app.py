import os
import datetime
import jwt
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import check_password_hash
from functools import wraps
from fpdf import FPDF
import io
from bson import ObjectId

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'super_secret_its_2026')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://attendance_db:27017/attendance_system')
client = MongoClient(MONGO_URI)
db = client.get_database()

# --- DECORATOR PER PROTEGGERE LE ROTTE ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token: return jsonify({'message': 'Token mancante'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.users.find_one({"username": data['username']})
        except: return jsonify({'message': 'Token non valido'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# --- CHIUSURA AUTOMATICA PER SCADENZA ORARIO ---
def auto_check_expiry():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    lesson = db.lessons.find_one({"date": today, "is_active": True})
    if lesson and current_time >= lesson['end_time']:
        db.lessons.update_one({"_id": lesson["_id"]}, {"$set": {"is_active": False}})
        db.presenze.update_many(
            {"date": today, "exit_time": None, "teacher": lesson['teacher']},
            {"$set": {"exit_time": lesson['end_time'], "status": "Uscita Automatica"}}
        )

# --- ROTTE AUTENTICAZIONE ---
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = db.users.find_one({"username": data.get('username')})
    if user and check_password_hash(user['password'], data.get('password')):
        token = jwt.encode({
            'username': user['username'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Credenziali errate'}), 401

@app.route('/api/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify({
        "username": current_user['username'], 
        "full_name": current_user.get('full_name'), 
        "materia": current_user.get('materia')
    }), 200

# --- GESTIONE SESSIONE LEZIONE ---
@app.route('/api/activate_lesson', methods=['POST'])
@token_required
def activate_lesson(current_user):
    data = request.json
    db.lessons.update_many({"is_active": True}, {"$set": {"is_active": False}})
    lesson_data = {
        "description": data.get('description'),
        "corso": data.get('corso'),
        "start_time": data.get('start_time'),
        "end_time": data.get('end_time'),
        "teacher": current_user['username'],
        "subject": current_user.get('materia', 'N.D.'),
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.datetime.now().timestamp(),
        "is_active": True
    }
    db.lessons.insert_one(lesson_data)
    return jsonify({"message": "Sessione avviata"}), 200

# --- CHIUSURA SESSIONE LEZIONE ---
@app.route('/api/deactivate_lesson', methods=['POST'])
@token_required
def deactivate_lesson(current_user):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H:%M")
    lesson = db.lessons.find_one({"teacher": current_user['username'], "is_active": True})
    
    if lesson:
        db.lessons.update_one({"_id": lesson["_id"]}, {"$set": {"is_active": False}})
        db.presenze.update_many(
            {"date": today, "teacher": current_user['username'], "lesson": lesson['description'], "exit_time": None},
            {"$set": {"exit_time": current_time, "status": "Chiusa da Docente"}}
        )
        return jsonify({"message": "Sessione terminata"}), 200
    return jsonify({"message": "Nessuna sessione attiva"}), 404

# --- STATO SESSIONE ATTIVA ---
@app.route('/api/active_session', methods=['GET'])
def get_active_session():
    auto_check_expiry()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    lesson = db.lessons.find_one({"date": today, "is_active": True})
    if lesson:
        user = db.users.find_one({"username": lesson['teacher']})
        return jsonify({
            "active": True,
            "teacher_display": user.get('full_name'),
            "subject": lesson.get('subject', 'N.D.'),
            "description": lesson['description'],
            "range": f"{lesson['start_time']} - {lesson['end_time']}"
        }), 200
    return jsonify({"active": False}), 200

# --- PRESENZE E STORICO ---
@app.route('/api/attendance/<teacher>/<lesson_desc>', methods=['GET'])
def get_attendance(teacher, lesson_desc):
    lesson = db.lessons.find_one({"teacher": teacher, "description": lesson_desc})
    if not lesson: return jsonify([]), 200
    presenze = list(db.presenze.find({
        "date": lesson['date'], "teacher": teacher, "lesson": lesson_desc
    }, {"_id": 0}).sort("entry_time", 1))
    return jsonify(presenze), 200

# --- STORICO LEZIONI ---
@app.route('/api/sessions_history', methods=['GET'])
@token_required
def get_history(current_user):
    history = list(db.lessons.find({"teacher": current_user['username']}, {"_id": 0}).sort("timestamp", -1))
    return jsonify(history), 200

# --- ESPORTAZIONE PDF ---
@app.route('/api/export_pdf', methods=['GET'])
def export_pdf():
    teacher_username = request.args.get('teacher')
    lesson_desc = request.args.get('lesson')
    filtro_stato = request.args.get('stato')      
    filtro_fuori = request.args.get('fuorisede')   
    include_ritirati = request.args.get('ritirati') == 'true' or request.args.get('ritirati') is None
    lesson = db.lessons.find_one({"teacher": teacher_username, "description": lesson_desc})
    if not lesson: 
        return "Lezione non trovata", 404
    teacher_data = db.users.find_one({"username": teacher_username})
    full_teacher_name = teacher_data.get('full_name', teacher_username)
    subject = lesson.get('subject', 'N.D.')
    corso_target = lesson.get('corso')
    date_lezione = lesson.get('date')
    query_studenti = {"metadata.corso": corso_target}
    if not include_ritirati:
        query_studenti["metadata.stato"] = "attivo"
    studenti_corso = list(db.users.find(query_studenti))
    presenze_registrate = db.presenze.distinct("username", {
        "date": date_lezione, "teacher": teacher_username, "lesson": lesson_desc
    })

    lista_finale = []
    for s in studenti_corso:
        is_presente = s['username'] in presenze_registrate
        meta = s.get('metadata', {})      
        include = True
        if filtro_stato == 'presenti' and not is_presente: include = False
        if filtro_stato == 'assenti' and is_presente: include = False
        if filtro_fuori and meta.get('fuorisede') != filtro_fuori: include = False
        if include:
            dettaglio = db.presenze.find_one({
                "username": s['username'], "lesson": lesson_desc, "date": date_lezione
            })
            lista_finale.append({
                "nome": f"{s.get('nome','')} {s.get('cognome','')}".upper(),
                "stato": "PRESENTE" if is_presente else "ASSENTE",
                "entrata": dettaglio['entry_time'] if is_presente else "--:--",
                "uscita": (dettaglio.get('exit_time') or "--:--") if is_presente and dettaglio else "--:--",
                "fuorisede": meta.get('fuorisede', 'N.D.').upper(),
                "condizione": meta.get('stato', 'attivo').upper()
            })

    # --- GENERAZIONE PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(79, 70, 229)
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(15)
    pdf.cell(190, 10, "ROL - Registro OffLine - ITS Academy Olivetti", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(190, 5, f"CORSO: {corso_target} | FILTRI ATTIVI: {filtro_stato or 'TUTTI'}", ln=True, align='C')
    pdf.set_y(60)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(63, 5, "DOCENTE", 0, 0, 'L')
    pdf.cell(63, 5, "MATERIA", 0, 0, 'L')
    pdf.cell(63, 5, "DATA LEZIONE", 0, 1, 'R')
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(63, 8, full_teacher_name.upper(), 0, 0, 'L')
    pdf.cell(63, 8, subject.upper(), 0, 0, 'L')
    pdf.cell(63, 8, date_lezione, 0, 1, 'R')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"Lezione: {lesson_desc}", ln=True)    
    pdf.ln(5)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(100, 116, 139)    
    pdf.cell(70, 10, " NOMINATIVO STUDENTE", 1, 0, 'L', True)
    pdf.cell(25, 10, "STATO", 1, 0, 'C', True)
    pdf.cell(25, 10, "ENTRATA", 1, 0, 'C', True)
    pdf.cell(25, 10, "USCITA", 1, 0, 'C', True)
    pdf.cell(25, 10, "F. SEDE", 1, 0, 'C', True)
    pdf.cell(20, 10, "NOTE", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 9)
    for row in lista_finale:
        if row['stato'] == "ASSENTE":
            pdf.set_fill_color(254, 242, 242)
            pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(70, 10, f" {row['nome']}", 1, 0, 'L', True)
        if row['stato'] == "ASSENTE":
            pdf.set_text_color(220, 38, 38)
        else:
            pdf.set_text_color(22, 163, 74)
        pdf.cell(25, 10, row['stato'], 1, 0, 'C', True)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(25, 10, row['entrata'], 1, 0, 'C', True)
        pdf.cell(25, 10, row['uscita'], 1, 0, 'C', True)
        pdf.cell(25, 10, row['fuorisede'], 1, 0, 'C', True)        
        note = "RIT." if row['condizione'] == "RITIRATO" else ""
        pdf.cell(20, 10, note, 1, 1, 'C', True)

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=f"ROL_{lesson_desc}.pdf")
    
@app.route('/dashboard')
def render_dashboard():
    return render_template('dashboard.html')

# --- AVVIO SERVER CON CONTROLLO DI ESISTENZA DI DATABASE ---
if __name__ == '__main__':
    with app.app_context():
            try:
                if db.users.count_documents({}) == 0:
                    print("🆕 Database vuoto rilevato! Lancio popolamento iniziale...")
                    from init_db import init_db
                    init_db()
                    print("✅ Database popolato con successo.")
                else:
                    print("✨ Database già esistente, salto inizializzazione.")
            except Exception as e:
                print(f"⚠️ Errore durante l'inizializzazione DB: {e}")
    app.run(host='0.0.0.0', port=5000, debug=True)