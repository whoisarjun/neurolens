import argon2
from dotenv import load_dotenv
from flask import Flask, render_template
from llm import chatbot
from db_manager import db
from datetime import datetime, timedelta
from auth import utils as auth
import os
import tempfile
import uuid
import jwt

app = Flask(__name__, template_folder='pages')

# Upgrade to llama3:70b once computing power is increased
LLM_MODEL = 'llama3.1:8b'
IMAGE_SUMMARY_MODEL = 'gemma4:e4b'
TEMP_IMAGE_DIR = './temp_images'
ph = argon2.PasswordHasher()
load_dotenv()

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
    return render_template("home.html")

@app.route('/login', methods=['GET'])
def show_login_page():
    return render_template("login.html")

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
    return render_template("patients.html")

@app.route('/patients_data', methods=['GET'])
def patients_data():
    patients = db.get_all_patients()
    for p in patients:
        p['cognitive_history'] = db.get_full_cognitive_history(p['id'])
        p['question_history'] = db.get_full_question_history(p['id'])
        p['image_summaries'] = db.get_full_image_summaries(p['id'])
        p['next_questions'] = db.get_next_questions(p['id'])
    return jsonify({'patients': patients})

def prep_next_questions(patient_data, max_entries=50):
    for i in ['patient_id', 'patient_password', 'caregiver_password', 'next_questions']:
        patient_data.pop(i, None)
    patient_data["cognitive_history"] = db.get_trimmed_cognitive_history(patient_data["id"], max_entries)
    patient_data["recent_question_history"] = db.get_full_question_history(patient_data["id"])[-max_entries:]
    patient_data["image_summaries"] = [
        entry["summary"] for entry in db.get_random_image_summaries(patient_data["id"], 5)
    ]
    print(f"[QUESTIONS] Preparing next questions for patient_id={patient_data['id']}", flush=True)
    qns = chatbot.new_questions(patient_data, model=LLM_MODEL)
    if not isinstance(qns, list) or len(qns) != 5 or not all(isinstance(q, str) and q.strip() for q in qns):
        raise ValueError(f"Expected 5 generated questions, got: {qns}")
    print(f"[QUESTIONS] Generated and validated 5 questions for patient_id={patient_data['id']}", flush=True)
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
    if patient_id != request.patient_id:
        return {'error': 'patient_id does not match authenticated user'}, 403

    features = payload.get('features')
    if not isinstance(features, list) or not features:
        return {'error': 'features must be a non-empty list of numbers'}, 400
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in features):
        return {'error': 'features must contain only numbers'}, 400

    answers = payload.get('transcript_text')
    if not isinstance(answers, list) or not answers:
        return {'error': 'transcript_text must be a non-empty list of strings'}, 400
    if not all(isinstance(answer, str) for answer in answers):
        return {'error': 'transcript_text must contain only strings'}, 400

    patient = db.get_patient_by_id(patient_id)
    if not patient:
        return {'error': f'Patient ID {patient_id} not found'}, 404

    db.append_cognitive_history(patient_id, features)

    # Fetch next_questions before updating
    next_qns = db.get_next_questions(patient_id)

    db.append_question_history(patient_id, next_qns, answers)

    try:
        updated_next_qns = prep_next_questions(dict(patient))
    except Exception as exc:
        return {
            'error': 'Failed to generate next questions',
            'details': str(exc)
        }, 502
    db.update_next_questions(patient_id, updated_next_qns)

    return {
        'message': f'Data appended for patient {patient_id}',
        'next_questions': updated_next_qns
    }, 200

@app.route('/create', methods=['GET'])
def create_patient():
    return render_template("create.html")

@app.route('/create_patient', methods=['POST'])
def create_patient_api():
    data = request.get_json()
    if not data:
        return {'error': 'No JSON payload received'}, 400

    required_fields = [
        'patient_id',
        'patient_password',
        'caregiver_password',
        'full_name',
        'first_name',
        'age',
        'gender'
    ]
    missing_fields = [field for field in required_fields if field not in data or data[field] in (None, '')]
    if missing_fields:
        return {'error': f"Missing fields: {', '.join(missing_fields)}"}, 400

    patient_id = data['patient_id']
    patient_password = ph.hash(data['patient_password'])
    caregiver_password = ph.hash(data['caregiver_password'])
    full_name = data['full_name']
    first_name = data['first_name']

    try:
        age = int(data['age'])
    except (TypeError, ValueError):
        return {'error': 'age must be an integer'}, 400

    gender = data['gender']

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

    try:
        updated_next_qns = prep_next_questions(dict(patient))
    except Exception as exc:
        return {
            'error': 'Patient created, but failed to generate initial questions',
            'details': str(exc)
        }, 502
    db.update_next_questions(patient_id, updated_next_qns)

    return {
        'message': f'Patient {patient_id} created successfully',
        'next_questions': updated_next_qns
    }, 201

@app.route('/upload_patient_images', methods=['POST'])
@require_jwt(required_role='caregiver')
def upload_patient_images():
    patient = db.get_patient_by_id(request.patient_id)
    if not patient:
        return {'error': f'Patient ID {request.patient_id} not found'}, 404

    files = request.files.getlist('image')
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        return {'error': 'Missing image files. Use repeated form field name "image".'}, 400

    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

    stored_summaries = []
    errors = []

    for file in valid_files:
        suffix = os.path.splitext(file.filename)[1] or '.jpg'
        temp_path = os.path.join(TEMP_IMAGE_DIR, f'{uuid.uuid4().hex}{suffix}')
        try:
            file.save(temp_path)
            print(
                f"[IMAGES] Saved upload for patient_id={request.patient_id} to {temp_path}",
                flush=True,
            )
            summary = chatbot.summarize_image(temp_path, model=IMAGE_SUMMARY_MODEL)
            stored_summaries.append(db.append_image_summary(request.patient_id, summary))
        except Exception as exc:
            errors.append({
                'filename': file.filename,
                'error': str(exc),
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"[IMAGES] Deleted temp file {temp_path}", flush=True)

    if not stored_summaries:
        return {
            'error': 'Failed to process uploaded images',
            'details': errors,
        }, 502

    status_code = 200 if not errors else 207
    return {
        'message': f'Processed {len(stored_summaries)} images',
        'summaries': stored_summaries,
        'errors': errors,
    }, status_code

@app.route('/patient_image_summaries', methods=['GET'])
@require_jwt(required_role='caregiver')
def get_patient_image_summaries():
    patient = db.get_patient_by_id(request.patient_id)
    if not patient:
        return {'error': f'Patient ID {request.patient_id} not found'}, 404

    return {
        'patient_id': request.patient_id,
        'image_summaries': db.get_full_image_summaries(request.patient_id),
    }, 200

@app.route('/next_questions', methods=['GET'])
@require_jwt(required_role='patient')
def get_next_questions():
    patient = db.get_patient_by_id(request.patient_id)
    if not patient:
        return {'error': f'Patient ID {request.patient_id} not found'}, 404

    return {
        'patient_id': request.patient_id,
        'next_questions': db.get_next_questions(request.patient_id)
    }, 200

@app.route('/pull_cognitive_history', methods=['POST'])
@require_jwt(required_role='caregiver')
def pull_cognitive_history():
    payload = request.get_json()
    if not payload:
        return {'error': 'No JSON payload received'}, 400

    patient_id = payload.get('patient_id')
    days = payload.get('days')

    if not patient_id or days is None:
        return {'error': 'Missing patient_id or days'}, 400

    full_history = db.get_full_cognitive_history(patient_id)

    if days == -1:
        return {'cognitive_history': full_history}

    cutoff_date = datetime.now() - timedelta(days=days)

    filtered_history = [
        entry for entry in full_history
        if datetime.fromisoformat(entry['date']) >= cutoff_date
    ]

    return {'cognitive_history': filtered_history}

# DELETE BEFORE PUBLISH (THIS IS JUST FOR DEVELOPMENT PURPOSES)
@app.route('/clear_patients', methods=['POST'])
def clear_patients():
    db.hard_clear()
    return {'message': 'Cleared all patients and related data'}, 200

if __name__ == '__main__':
    app.run(port=6767, debug=True)
