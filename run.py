from flask import Flask, request
from flask import render_template_string
from datetime import datetime
from llm import chatbot
import json
import os
import copy

app = Flask(__name__)

DATA_FILE = 'user_data.json'

def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {'data': []}
    return {'data': []}

def save_user_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Home page route
@app.route('/')
def home():
    return render_template_string('''
        <html>
            <head><title>Neurolens</title></head>
            <body>
                <h1>Welcome to Neurolens</h1>
                <a href='/patients'><button>View Patients</button></a>
            </body>
        </html>
    ''')

# View patients route
@app.route('/patients')
def view_patients():
    user_file = load_user_data()
    return render_template_string(f'''
        <html>
            <head><title>All Patient Data</title></head>
            <body>
                <h2>All Stored Patient Data</h2>
                <a href='/'><button>Back</button></a>
                <pre>{json.dumps(user_file, indent=4)}</pre>
            </body>
        </html>
    ''')

def find_patient_by_id(patient_id, patients_list):
    for p in patients_list:
        if p.get('patient_id') == patient_id:
            return p
    return None

def append_cognitive_entry(patient, features):
    entry = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'features': features
    }
    patient.setdefault('cognitive_history', []).append(entry)

def get_last_used_questions(patient):
    questions = []
    if patient.get('question_history'):
        last_entry = patient['question_history'][-1]
        questions = [q['q'] for q in last_entry.get('next_questions', [])]
    if not questions:
        questions = patient.get('next_questions', [])
    return questions

def append_question_entry(patient, questions, answers, question_limit=7):
    paired = [{'q': q, 'a': a} for q, a in zip(questions, answers)]
    entry = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'questions': paired
    }
    patient.setdefault('question_history', []).append(entry)
    if len(patient['question_history']) > question_limit:
        patient['question_history'].pop(0)

def prep_next_questions(patient_data, max_entries=50, questions=5):
    for i in ['patient_id', 'patient_password', 'caregiver_password', 'next_questions']:
        del patient_data[i]
    history = patient_data.get('cognitive_history', [])
    if len(history) > max_entries:
        patient_data['cognitive_history'] = history[-max_entries:]
    qns = chatbot.chat(f'''
    You are an expert cognitive health assistant. Your job is to generate exactly {questions} memory recall questions to ask an elderly patient at risk for dementia.

    Patient data:
    {patient_data}

    Your questions must:
    - Help the patient recall specific events or experiences from their past (short-term or long-term).
    - Avoid all reasoning, productivity, work, or technology-related topics.
    - Some questions should be emotionally engaging and personally meaningful (e.g., family, school, food, friends, places, holidays, etc).
    - Combine a mixture of short-term and long-term memory questions.
    - You should act as if you are a friend to the user.
    - Do NOT include your internal thoughts, planning steps, or commentary — only output the questions. Literally JUST the questions and NOTHING else.
    - Output exactly {questions} questions separated by newline characters (\n), no numbering or bullet points.
    - The user will be reading these questions the next day.
    - Remember that the user is likely an elderly person at risk or suffering with dementia, so your questions should be simple to understand and not complex.
    - DO NOT repeat questions that have already been asked.

    Example format:
    What is your favorite childhood memory?\nWhat was the last meal you really enjoyed?\n...
    ''', model='deepseek-r1:32b')
    return [q.lstrip(" 0123456789.").strip() for q in qns.split('\n')[-questions:] if q.strip()]

@app.route('/process_patient_data', methods=['POST'])
def process_data():
    payload = request.get_json()
    if not payload:
        return {'error': 'No JSON payload received'}, 400

    patient_id = payload.get('patient_id')
    if not patient_id:
        return {'error': 'Missing patient_id'}, 400

    user_file = load_user_data()
    patients_list = user_file.get('data', [])

    patient = find_patient_by_id(patient_id, patients_list)
    if not patient:
        return {'error': f'Patient ID {patient_id} not found'}, 404

    append_cognitive_entry(patient, payload['features'])

    questions = get_last_used_questions(patient)
    answers = payload.get('transcript_text', [])
    append_question_entry(patient, questions, answers)

    patient['next_questions'] = prep_next_questions(copy.deepcopy(patient))

    save_user_data(user_file)
    return {'message': f'Data appended for patient {patient_id}'}, 200

if __name__ == '__main__':
    app.run(port=6767, debug=True)