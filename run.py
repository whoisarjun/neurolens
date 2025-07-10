from flask import Flask, request
from flask import render_template_string
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "user_data.json"

def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"data": []}
    return {"data": []}

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Home page route
@app.route('/')
def home():
    return render_template_string("""
        <html>
            <head><title>Neurolens</title></head>
            <body>
                <h1>Welcome to Neurolens</h1>
                <a href="/patients"><button>View Patients</button></a>
            </body>
        </html>
    """)

# View patients route
@app.route('/patients')
def view_patients():
    user_file = load_user_data()
    return render_template_string(f"""
        <html>
            <head><title>All Patient Data</title></head>
            <body>
                <h2>All Stored Patient Data</h2>
                <a href='/'><button>Back</button></a>
                <pre>{json.dumps(user_file, indent=4)}</pre>
            </body>
        </html>
    """)

@app.route('/process_patient_data', methods=['POST'])
def process_data():
    payload = request.get_json()
    if not payload:
        return {"error": "No JSON payload received"}, 400

    patient_id = payload.get("patient_id")
    if not patient_id:
        return {"error": "Missing patient_id"}, 400

    user_file = load_user_data()
    patients_list = user_file.get("data", [])

    # Find patient object by patient_id in list
    patient = None
    for p in patients_list:
        if p.get("patient_id") == patient_id:
            patient = p
            break

    if not patient:
        return {"error": f"Patient ID {patient_id} not found"}, 404

    cognitive_entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "features": payload["features"]
    }
    patient.setdefault("cognitive_history", []).append(cognitive_entry)

    # Get last used questions from most recent question_history entry
    questions = []
    if patient.get("question_history"):
        last_entry = patient["question_history"][-1]
        questions = [q["q"] for q in last_entry.get("next_questions", [])]
    # Fallback to next_questions if last_entry empty
    if not questions:
        questions = patient.get("next_questions", [])
    answers = payload.get("transcript_text", [])
    paired = [{"q": q, "a": a} for q, a in zip(questions, answers)]

    question_entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "questions": paired
    }
    patient.setdefault("question_history", []).append(question_entry)
    if len(patient["question_history"]) > 3:
        patient["question_history"].pop(0)

    patient["next_questions"] = []

    save_user_data(user_file)
    return {"message": f"Data appended for patient {patient_id}"}, 200

if __name__ == '__main__':
    app.run(port=6767, debug=True)