import os
import json
import sqlite3
from dotenv import load_dotenv

load_dotenv()

conn = sqlite3.connect('../neurolens.db')
conn.execute(f'PRAGMA key = \'{os.getenv("SQLCIPHER_KEY")}\';')

def create_new_patient(patient_id, patient_password, caregiver_password, full_name, first_name, age, gender):
    conn.execute("""
        INSERT INTO patients (
            id, patient_password, caregiver_password,
            full_name, first_name, age, gender, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        patient_password,
        caregiver_password,
        full_name,
        first_name,
        age,
        gender,
        ""
    ))

    # empty next questions
    empty_next_qns = json.dumps([])

    conn.execute("""
        INSERT INTO next_questions (patient_id, questions_json)
        VALUES (?, ?)
    """, (patient_id, empty_next_qns))

    conn.commit()
    print(f"✅ Created user {patient_id} with empty history.")

