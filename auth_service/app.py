import os
import datetime
import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import check_password_hash

app = Flask(__name__)
CORS(app)

# config
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'secret')
client = MongoClient(os.getenv('MONGO_URI'))
db = client.get_database()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = db.users.find_one({'username': data.get('username')})

    # if match
    if user and check_password_hash(user['password'], data.get('password')):
        token = jwt.encode({
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token}), 200

    return jsonify({'message': 'Credenziali errate'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)