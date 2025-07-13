import argon2
from flask import Flask, render_template, render_template_string, redirect
from llm import chatbot
from db_manager import db
from feature_extraction import send_audio_data as audio
from auth import utils as auth
import os
import glob
import jwt
import json

app = Flask(__name__, template_folder='pages')

LLM_MODEL = 'deepseek-r1:32b'
ph = argon2.PasswordHasher()

from functools import wraps
from flask import request, jsonify

# decorator func just to restrict the functions here to the specific role that can access it
def require_jwt(required_role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid token'}), 401

            token = auth_header.split()[1]
            try:
                payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401

            if required_role and payload.get('role') != required_role:
                return jsonify({'error': 'Unauthorized role'}), 403

            request.patient_id = payload['patient_id']
            request.role = payload['role']

            return f(*args, **kwargs)
        return wrapper
    return decorator

# Home page route
@app.route('/')
def home():
    return render_template_string('''
        <html>
            <head><title>Neurolens</title></head>
            <body>
                <h1>Welcome to Neurolens</h1>
                <a href='/patients'><button>View Patients</button></a>
                <a href='/create'><button>Create New Patient</button></a>
                <br><br><br>
                <form method="POST" action="/clear_patients" onsubmit="return confirm('Are you sure you want to clear ALL patients?');">
                    <input type="submit" style="background-color:red;color:white;" value="CLEAR PATIENTS">
                </form>
            </body>
        </html>
    ''')

@app.route('/login', methods=['GET'])
def show_login_page():
    return '''
        <h2>Login</h2>
        <form method="POST" action="/auth/login">
            Patient ID: <input name="patient_id" type="text"><br>
            Password: <input name="password" type="password"><br>
            Role: <select name="role">
                <option value="patient">Patient</option>
                <option value="caregiver">Caregiver</option>
            </select><br>
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    patient_id = data.get('patient_id')
    password = data.get('password')
    role = data.get('role')  # 'patient' or 'caregiver'

    patient = db.get_patient_by_id(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    try:
        if role == 'patient':
            ph.verify(patient['patient_password'], password)
        elif role == 'caregiver':
            ph.verify(patient['caregiver_password'], password)
        else:
            return jsonify({'error': 'Invalid role'}), 400
    except:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'access_token': auth.generate_access_token(patient_id, role),
        'refresh_token': auth.generate_refresh_token(patient_id, role)
    })

@app.route('/auth/refresh', methods=['POST'])
def refresh():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid refresh token'}), 401

    token = auth_header.split()[1]

    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401

    if payload.get('token_type') != 'refresh':
        return jsonify({'error': 'Not a refresh token'}), 401

    # ensure the token is still in the db
    patient_id = auth.is_valid_refresh_token(token)
    if not patient_id:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401

    # allg – remove old rt and issue new tokens
    auth.delete_refresh_token(token)

    new_access = auth.generate_access_token(payload["patient_id"], payload["role"])
    new_refresh = auth.generate_refresh_token(payload["patient_id"], payload["role"])

    return jsonify({
        'access_token': new_access,
        'refresh_token': new_refresh
    })

# View patients route
@app.route('/patients')
def view_patients():
    patients = db.get_all_patients()
    for p in patients:
        p['cognitive_history'] = db.get_full_cognitive_history(p['id'])
        p['question_history'] = db.get_full_question_history(p['id'])
        p['next_questions'] = db.get_next_questions(p['id'])
    return render_template("patients.html", patients=patients)

def prep_next_questions(patient_data, max_entries=50):
    for i in ['patient_id', 'patient_password', 'caregiver_password', 'next_questions']:
        patient_data.pop(i, None)
    patient_data["cognitive_history"] = db.get_trimmed_cognitive_history(patient_data["id"], max_entries)
    qns = chatbot.new_questions(patient_data, model=LLM_MODEL)
    return qns

@app.route('/process_patient_data', methods=['POST'])
@require_jwt(required_role='patient')
def process_data():
    payload = request.get_json()
    if not payload:
        return {'error': 'No JSON payload received'}, 400

    patient_id = payload.get('patient_id')
    if not patient_id:
        return {'error': 'Missing patient_id'}, 400

    patient = db.get_patient_by_id(patient_id)
    if not patient:
        return {'error': f'Patient ID {patient_id} not found'}, 404

    db.append_cognitive_history(patient_id, payload['features'])

    # Fetch next_questions before updating
    next_qns = db.get_next_questions(patient_id)

    answers = payload.get('transcript_text', [])
    db.append_question_history(patient_id, next_qns, answers)

    updated_next_qns = prep_next_questions(dict(patient))
    db.update_next_questions(patient_id, updated_next_qns)

    return {'message': f'Data appended for patient {patient_id}'}, 200

@app.route('/create', methods=['GET', 'POST'])
def create_patient():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        patient_password = ph.hash(request.form['patient_password'])
        caregiver_password = ph.hash(request.form['caregiver_password'])
        full_name = request.form['full_name']
        first_name = request.form['first_name']
        age = int(request.form['age'])
        gender = request.form['gender']

        db.create_new_patient(
            patient_id=patient_id,
            patient_password=patient_password,
            caregiver_password=caregiver_password,
            full_name=full_name,
            first_name=first_name,
            age=age,
            gender=gender
        )

        patient = db.get_patient_by_id(patient_id)
        if not patient:
            return {'error': f'Patient ID {patient_id} not found'}, 404
        updated_next_qns = prep_next_questions(dict(patient))
        db.update_next_questions(patient_id, updated_next_qns)

        return f"✅ Patient {patient_id} created successfully!"

    return '''
    <h2>Create New Patient</h2>
    <form method="POST">
        Patient ID: <input type="text" name="patient_id"><br>
        Patient Password: <input type="text" name="patient_password"><br>
        Caregiver Password: <input type="text" name="caregiver_password"><br>
        Full Name: <input type="text" name="full_name"><br>
        First Name: <input type="text" name="first_name"><br>
        Age: <input type="number" name="age"><br>
        Gender: <input type="text" name="gender"><br>
        <input type="submit" value="Create Patient">
    </form>
    <a href="/"><button>Back</button></a>
    '''

@app.route('/upload_audio', methods=['POST'])
@require_jwt(required_role='patient')
def upload_audio():
    patient_id = request.form.get('patient_id')
    files = request.files.getlist('audio')

    if not patient_id or not files:
        return {'error': 'Missing patient_id or audio files'}, 400

    file_paths = []

    for idx, file in enumerate(files):
        filename = f"{patient_id}_q{idx+1}.wav"
        filepath = f"./temp/{filename}"
        file.save(filepath)
        file_paths.append(filepath)

    # Run feature extraction on each file
    result = audio.extract_features(file_paths, patient_id)
    audio.send_to_server(
        result,
        post_url='http://localhost:6767/process_patient_data',
        auth_headers=request.headers.get('Authorization')
    )

    files = glob.glob('./temp/*')
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"Failed to delete {f}: {e}")

    return {'message': f"Processed {len(files)} audio files, sent to server"}, 200

@app.route('/generate_report', methods=['POST'])
@require_jwt(required_role='caregiver')
def generate_report():
    payload = request.get_json()
    if not payload:
        return {'error': 'No JSON payload received'}, 400

    patient_id = payload.get('patient_id')
    days = payload.get('days')

    if not patient_id or days is None:
        return {'error': 'Missing patient_id or days'}, 400

    patient = db.get_patient_by_id(patient_id)
    if not patient:
        return {'error': f'Patient ID {patient_id} not found'}, 404

    full_cog_history = db.get_trimmed_cognitive_history(patient_id, days)
    full_qn_history = db.get_full_question_history(patient_id)

    recent_cog = full_cog_history[-30:]
    older_cog = full_cog_history[:-30] if len(full_cog_history) > 30 else []

    recent_qn = full_qn_history[-30:]
    # (optional: summarize question history too, but keeping it raw for now)

    def summarize(history):
        from statistics import mean
        if not history:
            return {}
        summary = {}
        keys = history[0].keys()
        for k in keys:
            vals = [h[k] for h in history if isinstance(h[k], (int, float))]
            if vals:
                summary[k] = {
                    "avg": round(mean(vals), 3),
                    "min": min(vals),
                    "max": max(vals)
                }
        return summary

    summary_cog = summarize(older_cog)

    patient_data = {
        "patient_info": {
            "full_name": patient.get('full_name'),
            "age": patient.get('age'),
            "gender": patient.get('gender')
        },
        "recent_cognitive_history": recent_cog,
        "yearly_summary": summary_cog,
        "recent_question_history": recent_qn
    }

    result = chatbot.generate_report(patient_data, days, model=LLM_MODEL)

    return {'report': result}

# DELETE BEFORE PUBLISH (THIS IS JUST FOR DEVELOPMENT PURPOSES)
@app.route('/clear_patients', methods=['POST'])
def clear_patients():
    db.hard_clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(port=6767, debug=True)