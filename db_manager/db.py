import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Remove old DB_PATH and set_path for SQLite

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

def create_new_patient(patient_id, patient_password, caregiver_password, full_name, first_name, age, gender):

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO patients (
            id, patient_password, caregiver_password,
            full_name, first_name, age, gender, description
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Created user {patient_id} with empty history.")

def get_all_patients():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_patient_by_id(patient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
    row = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    if row:
        return dict(zip(columns, row))
    return None

def append_cognitive_history(patient_id, features_dict, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cognitive_history (patient_id, date, features_json) VALUES (%s, %s, %s)",
        (patient_id, date, json.dumps(features_dict))
    )
    conn.commit()
    cursor.close()
    conn.close()

def append_question_history(patient_id, questions, answers, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    qa_pairs = [{"q": q, "a": a} for q, a in zip(questions, answers)]
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO question_history (patient_id, date, questions_json) VALUES (%s, %s, %s)",
        (patient_id, date, json.dumps(qa_pairs))
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_next_questions(patient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT questions_json FROM next_questions WHERE patient_id = %s", (patient_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row and row[0]:
        return row[0]
    return []

def update_next_questions(patient_id, questions):
    qns_json = json.dumps(questions)
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM next_questions WHERE patient_id = %s", (patient_id,))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("UPDATE next_questions SET questions_json = %s WHERE patient_id = %s", (qns_json, patient_id))
    else:
        cursor.execute("INSERT INTO next_questions (patient_id, questions_json) VALUES (%s, %s)", (patient_id, qns_json))
    conn.commit()
    cursor.close()
    conn.close()

def get_trimmed_cognitive_history(patient_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT features_json FROM cognitive_history
        WHERE patient_id = %s
        ORDER BY date DESC
        LIMIT %s
    """, (patient_id, limit))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in rows]

def get_full_cognitive_history(patient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT date, features_json FROM cognitive_history WHERE patient_id = %s ORDER BY date DESC", (patient_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"date": r[0], "features": r[1]} for r in rows]

def get_full_question_history(patient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, questions_json FROM question_history WHERE patient_id = %s ORDER BY date DESC",
        (patient_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "qa": r[1]} for r in rows]

def hard_clear():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cognitive_history")
    cursor.execute("DELETE FROM question_history")
    cursor.execute("DELETE FROM next_questions")
    cursor.execute("DELETE FROM patients")
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Cleared all patients and related data.")
