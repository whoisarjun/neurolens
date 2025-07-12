import jwt
import os
import datetime as dt

def generate_access_token(patient_id, role):
    payload = {
        'patient_id': patient_id,
        'role': role,
        'exp': dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            minutes=int(os.getenv("ACCESS_TOKEN_LIFETIME"))
        )
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')
    return token