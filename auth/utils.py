import jwt
import os
import datetime as dt
from dotenv import load_dotenv
from db_manager import db

load_dotenv()
supabase = db.supabase

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
    # expires_at can be a string or datetime; Supabase can handle ISO-ish strings.
    data = {
        'patient_id': patient_id,
        'token': token,
        'expires_at': expires_at,
    }

    response = supabase.table('refresh_tokens').insert(data).execute()

    if getattr(response, 'error', None):
        raise Exception(f"Failed to store refresh token for {patient_id}: {response.error}")


def is_valid_refresh_token(token):
    # Try to get a single matching row; if none, it's invalid.
    response = (
        supabase.table('refresh_tokens')
        .select('patient_id, expires_at')
        .eq('token', token)
        .maybe_single()
        .execute()
    )

    if getattr(response, 'error', None):
        raise Exception(f"Failed to validate refresh token: {response.error}")

    row = response.data
    if not row:
        return None

    expires_at = row['expires_at']

    # Handle both stored-as-string and datetime/iso formats defensively
    if isinstance(expires_at, str):
        # Supabase often returns ISO8601; if you formatted as "%Y-%m-%d %H:%M:%S", this also works.
        try:
            expires_at = dt.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            expires_at = dt.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)

    if dt.datetime.now(dt.timezone.utc) > expires_at:
        return None

    return row['patient_id']


def delete_refresh_token(token):
    response = (
        supabase.table('refresh_tokens')
        .delete()
        .eq('token', token)
        .execute()
    )

    if getattr(response, 'error', None):
        raise Exception(f"Failed to delete refresh token: {response.error}")

