import jwt
import os
import datetime as dt

from db_manager import db

def generate_access_token(patient_id, role):
    payload = {
        'patient_id': patient_id,
        'role': role,
        'exp': dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            minutes=int(os.getenv("ACCESS_TOKEN_LIFETIME_MINS"))
        )
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')

def generate_refresh_token(patient_id, role):
    payload = {
        'patient_id': patient_id,
        'role': role,
        'token_type': 'refresh',
        'exp': dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            days=int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS"))
        )
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')

    # also store in DB
    expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        days=int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS"))
    )).strftime("%Y-%m-%d %H:%M:%S")
    store_refresh_token(patient_id, token, expires_at)

    return token

def store_refresh_token(patient_id, token, expires_at):
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_tokens (patient_id, token, expires_at) VALUES (%s, %s, %s)",
        (patient_id, token, expires_at)
    )
    conn.commit()
    conn.close()

def is_valid_refresh_token(token):
    conn = db.get_conn()
    cursor = conn.cursor()
    result = cursor.execute(
        "SELECT patient_id, expires_at FROM refresh_tokens WHERE token = %s", (token,)
    ).fetchone()
    if not result:
        conn.close()
        return None
    expires_at = result["expires_at"]
    if isinstance(expires_at, str):
        expires_at = dt.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    if dt.datetime.now(dt.timezone.utc) > expires_at:
        conn.close()
        return None
    conn.close()
    return result["patient_id"]

def delete_refresh_token(token):
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM refresh_tokens WHERE token = %s", (token,))
    conn.commit()
    conn.close()

