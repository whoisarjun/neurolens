import sqlite3
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = '../neurolens.db'  # adjust path as needed

def set_path(path):
    global DB_PATH
    DB_PATH = path

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_new_patient(patient_id, patient_password, caregiver_password, full_name, first_name, age, gender):
    conn = get_conn()
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

    empty_next_qns = json.dumps([])

    conn.execute("""
        INSERT INTO next_questions (patient_id, questions_json)
        VALUES (?, ?)
    """, (patient_id, empty_next_qns))

    conn.commit()
    conn.close()
    print(f"✅ Created user {patient_id} with empty history.")

def get_all_patients():
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM patients")
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_patient_by_id(patient_id):
    conn = get_conn()
    cursor = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    columns = [column[0] for column in cursor.description]
    conn.close()
    if row:
        return dict(zip(columns, row))
    return None

def append_cognitive_history(patient_id, features_dict, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_conn()
    conn.execute(
        "INSERT INTO cognitive_history (patient_id, date, features_json) VALUES (?, ?, ?)",
        (patient_id, date, json.dumps(features_dict))
    )
    conn.commit()
    conn.close()

def append_question_history(patient_id, questions, answers, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    qa_pairs = [{"q": q, "a": a} for q, a in zip(questions, answers)]
    conn = get_conn()
    conn.execute(
        "INSERT INTO question_history (patient_id, date, questions_json) VALUES (?, ?, ?)",
        (patient_id, date, json.dumps(qa_pairs))
    )
    conn.commit()
    conn.close()

def get_next_questions(patient_id):
    conn = get_conn()
    cursor = conn.execute("SELECT questions_json FROM next_questions WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []

def update_next_questions(patient_id, questions):
    qns_json = json.dumps(questions)
    conn = get_conn()
    cursor = conn.execute("SELECT 1 FROM next_questions WHERE patient_id = ?", (patient_id,))
    exists = cursor.fetchone()
    if exists:
        conn.execute("UPDATE next_questions SET questions_json = ? WHERE patient_id = ?", (qns_json, patient_id))
    else:
        conn.execute("INSERT INTO next_questions (patient_id, questions_json) VALUES (?, ?)", (patient_id, qns_json))
    conn.commit()
    conn.close()

def get_trimmed_cognitive_history(patient_id, limit=50):
    conn = get_conn()
    cursor = conn.execute("""
        SELECT features_json FROM cognitive_history
        WHERE patient_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (patient_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [json.loads(row[0]) for row in rows]

def get_full_cognitive_history(patient_id):
    conn = get_conn()
    cursor = conn.execute("SELECT date, features_json FROM cognitive_history WHERE patient_id = ? ORDER BY date DESC", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "features": json.loads(r[1])} for r in rows]

def get_full_question_history(patient_id):
    conn = get_conn()
    cursor = conn.execute("SELECT date, questions_json FROM question_history WHERE patient_id = ? ORDER BY date DESC", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "qa": json.loads(r[1])} for r in rows]

def get_next_questions(patient_id):
    conn = get_conn()
    cursor = conn.execute("SELECT questions_json FROM next_questions WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []
