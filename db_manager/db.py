import psycopg2
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_ROLE')
supabase = create_client(url, key)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

def create_new_patient(patient_id, patient_password, caregiver_password, full_name, first_name, age, gender):
    data = {
        'id': patient_id,
        'patient_password': patient_password,
        'caregiver_password': caregiver_password,
        'full_name': full_name,
        'first_name': first_name,
        'age': age,
        'gender': gender,
        'description': ''
    }

    response = supabase.table('patients').insert(data).execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to create user {patient_id}: {response.error}")

    print(f"✅ Created user {patient_id} with empty history.")
    return response.data

def get_all_patients():
    response = supabase.table('patients').select('*').execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to fetch patients: {response.error}")

    return response.data

def get_patient_by_id(patient_id):
    response = supabase.table('patients').select('*').eq('id', patient_id).single().execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to fetch patient {patient_id}: {response.error}")

    return response.data

def append_cognitive_history(patient_id, features_dict, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    data = {
        'patient_id': patient_id,
        'date': date,
        'features_json': features_dict
    }

    response = supabase.table('cognitive_history').insert(data).execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to append cognitive history for {patient_id}: {response.error}")

    print(f"✅ Appended cognitive history for {patient_id}.")
    return response.data

def append_question_history(patient_id, questions, answers, date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    qa_pairs = [{'q': q, 'a': a} for q, a in zip(questions, answers)]

    data = {
        'patient_id': patient_id,
        'date': date,
        'questions_json': qa_pairs
    }

    response = supabase.table('question_history').insert(data).execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to append question history for {patient_id}: {response.error}")

    print(f"✅ Appended question history for {patient_id}.")
    return response.data

def get_next_questions(patient_id):
    try:
        response = supabase.table('next_questions').select('questions_json').eq('patient_id',
                                                                                patient_id).single().execute()
    except Exception:
        return []

    if getattr(response, 'error', None):
        raise Exception(f"Failed to fetch next questions for {patient_id}: {response.error}")

    if response.data and response.data.get('questions_json'):
        return response.data['questions_json']
    return []

def update_next_questions(patient_id, questions):
    data = {
        'patient_id': patient_id,
        'questions_json': questions
    }

    response = supabase.table('next_questions').upsert(data, on_conflict='patient_id').execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to update next questions for {patient_id}: {response.error}")

    print(f"✅ Updated next questions for {patient_id}.")
    return response.data

def get_trimmed_cognitive_history(patient_id, limit=50):
    response = (
        supabase.table('cognitive_history')
        .select('features_json')
        .eq('patient_id', patient_id)
        .order('date', desc=True)
        .limit(limit)
        .execute()
    )

    if getattr(response, 'error', None):
        raise Exception(f"Failed to get trimmed cognitive history for {patient_id}: {response.error}")

    return [row['features_json'] for row in response.data]

def get_full_cognitive_history(patient_id):
    response = (
        supabase.table('cognitive_history')
        .select('date, features_json')
        .eq('patient_id', patient_id)
        .order('date', desc=True)
        .execute()
    )

    if getattr(response, 'error', None):
        raise Exception(f"Failed to get full cognitive history for {patient_id}: {response.error}")

    return [{'date': r['date'], 'features': r['features_json']} for r in response.data]

def get_full_question_history(patient_id):
    response = (
        supabase.table('question_history')
        .select('date, questions_json')
        .eq('patient_id', patient_id)
        .order('date', desc=True)
        .execute()
    )

    if getattr(response, 'error', None):
        raise Exception(f"Failed to get full question history for {patient_id}: {response.error}")

    return [{'date': r['date'], 'qa': r['questions_json']} for r in response.data]

def hard_clear():
    supabase.table('cognitive_history').delete().neq('id', 0).execute()
    supabase.table('question_history').delete().neq('id', 0).execute()
    supabase.table('next_questions').delete().neq('patient_id', '').execute()
    supabase.table('patients').delete().neq('id', '').execute()

    print("✅ Cleared all patients and related data.")

# ALL THE TABLES IN THE DB
#
# CREATE TABLE patients (
#   id text NOT NULL,
#   patient_password text NOT NULL,
#   caregiver_password text NOT NULL,
#   full_name text,
#   first_name text,
#   age integer,
#   gender text,
#   description text DEFAULT ''::text,
#   ,PRIMARY KEY (id)
# );
#
#
#
# CREATE TABLE next_questions (
#   patient_id text NOT NULL,
#   questions_json jsonb NOT NULL,
#   ,PRIMARY KEY (patient_id)
# );
#
#
#
# CREATE TABLE cognitive_history (
#   id integer DEFAULT nextval('cognitive_history_id_seq'::regclass) NOT NULL,
#   patient_id text,
#   date text NOT NULL,
#   features_json jsonb NOT NULL,
#   ,PRIMARY KEY (id)
# );
#
#
#
# CREATE TABLE question_history (
#   id integer DEFAULT nextval('question_history_id_seq'::regclass) NOT NULL,
#   patient_id text,
#   date text NOT NULL,
#   questions_json jsonb NOT NULL,
#   ,PRIMARY KEY (id)
# );
#
#
#
# CREATE TABLE refresh_tokens (
#   patient_id text NOT NULL,
#   token text NOT NULL,
#   expires_at timestamp without time zone NOT NULL,
#   ,PRIMARY KEY (token)
# );