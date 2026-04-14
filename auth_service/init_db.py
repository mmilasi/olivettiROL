from pymongo import MongoClient
from werkzeug.security import generate_password_hash

client = MongoClient('mongodb://localhost:27017/')
db = client.get_database('attendance_system')
users_collection = db.users

def create_admin():
    username = "docente_its"
    password = "password123"
    
    if users_collection.find_one({'username': username}):
        print(f"Utente {username} già esistente.")
        return

    hashed_password = generate_password_hash(password)
    
    user_data = {
        'username': username,
        'password': hashed_password,
        'role': 'teacher',
        'created_at': '2026-04-09'
    }
    
    users_collection.insert_one(user_data)
    print(f"Utente {username} creato con successo!")

if __name__ == "__main__":
    create_admin()