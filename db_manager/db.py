import json
import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "neurolens.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _row_to_dict(row):
    return dict(row) if row is not None else None

def _serialize_json(value):
    return json.dumps(value)

def _deserialize_json(value, default):
    if value is None:
        return default
    return json.loads(value)

def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                patient_password TEXT NOT NULL,
                caregiver_password TEXT NOT NULL,
                full_name TEXT,
                first_name TEXT,
                age INTEGER,
                gender TEXT,
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS next_questions (
                patient_id TEXT PRIMARY KEY,
                questions_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cognitive_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                date TEXT NOT NULL,
                features_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS question_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                date TEXT NOT NULL,
                questions_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS patient_image_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                date TEXT NOT NULL,
                summary_text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )
        conn.commit()

def create_new_patient(patient_id, patient_password, caregiver_password, full_name, first_name, age, gender):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO patients (
                id, patient_password, caregiver_password, full_name,
                first_name, age, gender, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, patient_password, caregiver_password, full_name, first_name, age, gender, ""),
        )
        conn.commit()

    print(f"Created user {patient_id} with empty history.")
    return get_patient_by_id(patient_id)

def get_all_patients():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()
    return [_row_to_dict(row) for row in rows]

def get_patient_by_id(patient_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    return _row_to_dict(row)

def append_cognitive_history(patient_id, features_dict, date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_history (patient_id, date, features_json)
            VALUES (?, ?, ?)
            """,
            (patient_id, date, _serialize_json(features_dict)),
        )
        conn.commit()

    print(f"Appended cognitive history for {patient_id}.")
    return {
        "id": cursor.lastrowid,
        "patient_id": patient_id,
        "date": date,
        "features_json": features_dict,
    }

def append_question_history(patient_id, questions, answers, date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    qa_pairs = [{"q": q, "a": a} for q, a in zip(questions, answers)]

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO question_history (patient_id, date, questions_json)
            VALUES (?, ?, ?)
            """,
            (patient_id, date, _serialize_json(qa_pairs)),
        )
        conn.commit()

    print(f"Appended question history for {patient_id}.")
    return {
        "id": cursor.lastrowid,
        "patient_id": patient_id,
        "date": date,
        "questions_json": qa_pairs,
    }

def get_next_questions(patient_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT questions_json FROM next_questions WHERE patient_id = ?",
            (patient_id,),
        ).fetchone()

    if not row:
        return []

    return _deserialize_json(row["questions_json"], [])

def update_next_questions(patient_id, questions):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO next_questions (patient_id, questions_json)
            VALUES (?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                questions_json = excluded.questions_json
            """,
            (patient_id, _serialize_json(questions)),
        )
        conn.commit()

    print(f"Updated next questions for {patient_id}.")
    return {"patient_id": patient_id, "questions_json": questions}

def get_trimmed_cognitive_history(patient_id, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT features_json
            FROM cognitive_history
            WHERE patient_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (patient_id, limit),
        ).fetchall()

    return [_deserialize_json(row["features_json"], {}) for row in rows]

def get_full_cognitive_history(patient_id):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, features_json
            FROM cognitive_history
            WHERE patient_id = ?
            ORDER BY date DESC, id DESC
            """,
            (patient_id,),
        ).fetchall()

    return [
        {"date": row["date"], "features": _deserialize_json(row["features_json"], {})}
        for row in rows
    ]

def get_full_question_history(patient_id):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, questions_json
            FROM question_history
            WHERE patient_id = ?
            ORDER BY date DESC, id DESC
            """,
            (patient_id,),
        ).fetchall()

    return [
        {"date": row["date"], "qa": _deserialize_json(row["questions_json"], [])}
        for row in rows
    ]

def append_image_summary(patient_id, summary_text, date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO patient_image_summaries (patient_id, date, summary_text)
            VALUES (?, ?, ?)
            """,
            (patient_id, date, summary_text),
        )
        conn.commit()

    print(f"Stored image summary for {patient_id}.")
    return {
        "id": cursor.lastrowid,
        "patient_id": patient_id,
        "date": date,
        "summary": summary_text,
    }

def get_full_image_summaries(patient_id):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, date, summary_text
            FROM patient_image_summaries
            WHERE patient_id = ?
            ORDER BY date DESC, id DESC
            """,
            (patient_id,),
        ).fetchall()

    return [
        {"id": row["id"], "date": row["date"], "summary": row["summary_text"]}
        for row in rows
    ]

def get_random_image_summaries(patient_id, limit=5):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, date, summary_text
            FROM patient_image_summaries
            WHERE patient_id = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (patient_id, limit),
        ).fetchall()

    return [
        {"id": row["id"], "date": row["date"], "summary": row["summary_text"]}
        for row in rows
    ]

def store_refresh_token(patient_id, token, expires_at):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens (patient_id, token, expires_at)
            VALUES (?, ?, ?)
            """,
            (patient_id, token, expires_at),
        )
        conn.commit()

def get_refresh_token(token):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT patient_id, expires_at
            FROM refresh_tokens
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    return _row_to_dict(row)

def delete_refresh_token(token):
    with get_conn() as conn:
        conn.execute("DELETE FROM refresh_tokens WHERE token = ?", (token,))
        conn.commit()

def hard_clear():
    with get_conn() as conn:
        conn.execute("DELETE FROM cognitive_history")
        conn.execute("DELETE FROM question_history")
        conn.execute("DELETE FROM patient_image_summaries")
        conn.execute("DELETE FROM next_questions")
        conn.execute("DELETE FROM refresh_tokens")
        conn.execute("DELETE FROM patients")
        conn.commit()

    print("Cleared all patients and related data.")

init_db()
