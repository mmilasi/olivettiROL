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

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'super_secret_its_2026')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/attendance_system')

client = MongoClient(MONGO_URI)
db = client.get_database()

# --- DECORATOR PER PROTEGGERE LE ROTTE CHE RICHIEDONO AUTENTICAZIONE ---
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

# --- CHIUSURA AUTOMATICA DELLA LEZIONE IN ORARIO DI FINE (sincronizzata con orario Docker) ---
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

# --- ROTTE API ---
# --- AUTENTICAZIONE ---
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

# --- GESTIONE LEZIONI E PRESENZE ---
@app.route('/api/activate_lesson', methods=['POST'])
@token_required
def activate_lesson(current_user):
    data = request.json
    db.lessons.update_many({"is_active": True}, {"$set": {"is_active": False}})
    lesson_data = {
        "description": data.get('description'),
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

# --- VERIFICA SESSIONE ATTIVA PER LA DASHBOARD E IL TOTEM ---
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

# --- REGISTRAZIONE PRESENZA (TOTEM) ---
@app.route('/api/attendance/<teacher>/<lesson_desc>', methods=['GET'])
def get_attendance_by_lesson(teacher, lesson_desc):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    presenze = list(db.presenze.find({
        "date": today, 
        "teacher": teacher, 
        "lesson": lesson_desc
    }, {"_id": 0}).sort("entry_time", 1))
    return jsonify(presenze), 200

# --- DISATTIVAZIONE MANUALE DELLA LEZIONE ---
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
            {"$set": {"exit_time": current_time, "status": "Terminata dal Docente"}}
        )
        return jsonify({"message": "Sessione terminata con successo"}), 200
    
    return jsonify({"message": "Nessuna sessione attiva trovata"}), 404

# --- STORICO LEZIONI ---
@app.route('/api/sessions_history', methods=['GET'])
@token_required
def get_history(current_user):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    history = list(db.lessons.find({"date": today}, {"_id": 0}).sort("timestamp", -1))
    return jsonify(history), 200

# --- ESPORTAZIONE PDF ---
@app.route('/api/export_pdf', methods=['GET'])
def export_pdf():
    teacher = request.args.get('teacher')
    lesson_desc = request.args.get('lesson')
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    lesson = db.lessons.find_one({"date": date, "teacher": teacher, "description": lesson_desc})
    user = db.users.find_one({"username": teacher})
    presenze = list(db.presenze.find({"date": date, "teacher": teacher, "lesson": lesson_desc}).sort("entry_time", 1))

    pdf = FPDF()
    pdf.add_page()
    
    # --- SEZIONE GRAFICA PER IL PDF GENERATO ---
    pdf.set_fill_color(79, 70, 229)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(15)
    pdf.cell(190, 10, "ITS ATTENDANCE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"REPORT GENERATO IL {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(20)
    pdf.set_text_color(31, 41, 55)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"Dettaglio Lezione: {lesson_desc}", ln=True)
    pdf.set_draw_color(229, 231, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(107, 114, 128) 
    pdf.cell(45, 8, "DOCENTE", 0)
    pdf.cell(45, 8, "MATERIA", 0)
    pdf.cell(45, 8, "ORARIO PREVISTO", 0)
    pdf.cell(45, 8, "DATA", 0, 1)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(31, 41, 55) 
    pdf.cell(45, 8, user.get('full_name', teacher).upper(), 0)
    pdf.cell(45, 8, lesson.get('subject', 'N.D.').upper(), 0)
    pdf.cell(45, 8, f"{lesson.get('start_time')} - {lesson.get('end_time')}", 0)
    pdf.cell(45, 8, date, 0, 1)
    pdf.ln(15)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_text_color(71, 85, 105)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 12, "  NOMINATIVO STUDENTE", 1, 0, 'L', True)
    pdf.cell(45, 12, "ORARIO ENTRATA", 1, 0, 'C', True)
    pdf.cell(45, 12, "ORARIO USCITA", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(31, 41, 55)
    fill = False
    for p in presenze:
        if fill:
            pdf.set_fill_color(252, 252, 253)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(100, 10, f"  {p['student_name']}", 1, 0, 'L', True)
        pdf.cell(45, 10, p['entry_time'], 1, 0, 'C', True)
        pdf.cell(45, 10, p['exit_time'] or "---", 1, 1, 'C', True)
        fill = not fill
    pdf.set_y(-20)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(150)
    pdf.cell(0, 10, f"Documento ufficiale ITS Attendance System - Pagina {pdf.page_no()}", 0, 0, 'C')
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=f"Report_{lesson_desc}.pdf")

# --- ROTTE PER LA DASHBOARD ---
@app.route('/api/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify({"username": current_user['username'], "full_name": current_user.get('full_name'), "materia": current_user.get('materia')}), 200

# --- ROTTA PER RENDERIZZARE LA DASHBOARD (FRONTEND) ---
@app.route('/dashboard')
def render_dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)