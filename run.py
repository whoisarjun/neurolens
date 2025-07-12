from flask import Flask, request, render_template, render_template_string
from llm import chatbot
from db_manager import db
from feature_extraction import send_audio_data as audio

app = Flask(__name__, template_folder='pages')

MODEL = 'deepseek-r1:32b'

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
                <a href='/upload_audio'><button>Upload Audio</button></a>
            </body>
        </html>
    ''')

# View patients route
@app.route('/patients')
def view_patients():
    patients = db.get_all_patients()
    for p in patients:
        p['cognitive_history'] = db.get_full_cognitive_history(p['id'])
        p['question_history'] = db.get_full_question_history(p['id'])
        p['next_questions'] = db.get_next_questions(p['id'])
    return render_template("patients.html", patients=patients)

def prep_next_questions(patient_data, max_entries=50, questions=5):
    for i in ['patient_id', 'patient_password', 'caregiver_password', 'next_questions']:
        patient_data.pop(i, None)
    patient_data["cognitive_history"] = db.get_trimmed_cognitive_history(patient_data["id"], max_entries)
    qns = chatbot.chat(f'''
    You are an expert cognitive health assistant. Your job is to generate exactly {questions} memory recall questions to ask an elderly patient at risk for dementia.

    Patient data:
    {patient_data}

    Your questions must adhere to the following for them to be valid:
    - Help the patient recall specific events or experiences from their past (short-term or long-term).
    - Avoid all reasoning, productivity, work, or technology-related topics.
    - Some questions should be emotionally engaging and personally meaningful (e.g., family, school, food, friends, places, holidays, etc).
    - Combine a mixture of short-term (i.e. memories from the day or the week) and long-term memory questions (i.e. memories from the year or their childhood).
    - Of the {questions} questions:
        - At least 2 must be focused on short-term memory (e.g. events from today or this week)
        - At least 2 must be focused on long-term memory (e.g. events from childhood, past holidays, old routines)
        - 1 can be either.
    - You should act as if you are a friend to the user.
    - Do NOT include your internal thoughts, planning steps, or commentary — only output the questions. Literally JUST the questions and NOTHING else.
    - Output exactly {questions} questions separated by newline characters (\n), no numbering or bullet points.
    - The user will be reading these questions the next day.
    - Remember that the user is likely an elderly person at risk or suffering with dementia, so your questions should be simple to understand and not complex.
    - Do NOT repeat any questions that have been asked in the patient's question history. Use the question_history provided in the patient data to ensure all questions are fresh and unique. Repeating a question that has already been asked is considered a failure of the task.

    Example format:
    What is your favorite childhood memory?\nWhat was the last meal you really enjoyed?\n...
    ''', model=MODEL)
    return [q.lstrip(" 0123456789.").strip() for q in qns.split('\n')[-questions:] if q.strip()]

@app.route('/process_patient_data', methods=['POST'])
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
        patient_password = request.form['patient_password']
        caregiver_password = request.form['caregiver_password']
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

@app.route('/upload_audio', methods=['GET', 'POST'])
def upload_audio():
    if request.method == 'GET':
        return '''
        <h2>Upload audio files for patient</h2>
        <a href="/"><button>Back</button></a>
        <form method="POST" enctype="multipart/form-data">
            Patient ID: <input type="text" name="patient_id"><br><br>
            Audio 1: <input type="file" name="audio"><br>
            Audio 2: <input type="file" name="audio"><br>
            Audio 3: <input type="file" name="audio"><br>
            Audio 4: <input type="file" name="audio"><br>
            Audio 5: <input type="file" name="audio"><br><br>
            <input type="submit" value="Upload">
        </form>
        '''

    # post
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
    audio.send_to_server(result)

    return {'message': f"Processed {len(files)} audio files, sent to server"}, 200


if __name__ == '__main__':
    app.run(port=6767, debug=True)