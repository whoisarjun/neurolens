# Neurolens Backend

Neurolens is a Flask backend for a patient conversation workflow. It stores per-session feature vectors, keeps question and answer history, generates the next five questions for each patient, and exposes caregiver-facing history and image-summary endpoints.

The backend does not perform audio upload handling, explainability reporting, or interpret feature-vector indices. It expects the client or a separate pipeline to produce the final numeric feature list before submission.

## Documentation

- API reference: [API_GUIDE.md](./API_GUIDE.md)
- Feature extraction notes: [feature_extraction/readme.md](./feature_extraction/readme.md)

## Current Flow

1. A patient or caregiver logs in with `POST /auth/login`.
2. The client stores the returned JWT access and refresh tokens.
3. A patient fetches pending questions with `GET /next_questions`.
4. After answering the session, the client submits answers and features with `POST /process_patient_data`.
5. The backend stores the session, generates the next five questions, and returns them immediately.
6. A caregiver can retrieve cognitive history and image summaries for the patient tied to the authenticated token scope.

## API Surface

### Auth

- `POST /auth/login`
- `POST /auth/refresh`

### Patient

- `POST /process_patient_data`
- `GET /next_questions`

### Caregiver

- `POST /pull_cognitive_history`
- `POST /upload_patient_images`
- `GET /patient_image_summaries`

### Local Admin / UI Pages

- `GET /`
- `GET /login`
- `GET /patients`
- `GET /patients_data`
- `GET /create`
- `POST /create_patient`

## Data Model

The app uses SQLite by default.

- Default database path: `neurolens.db` in the project root
- Override with: `SQLITE_DB_PATH` in `.env`
- Tables are created automatically on startup

Stored data includes:

- Patient records and credentials
- Refresh tokens
- Cognitive feature history
- Question and answer history
- Current pending questions
- Image summaries generated from uploaded caregiver images

## Environment

The backend reads configuration from `.env`. At minimum, make sure these values exist:

- `JWT_SECRET`
- `ACCESS_TOKEN_LIFETIME_MINS`
- `REFRESH_TOKEN_LIFETIME_DAYS`
- `SQLITE_DB_PATH` (optional)

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Create a `.env` file with the required settings.
4. Start the server with `python run.py`.

By default, the Flask app runs on `http://localhost:6767`.

## Notes

- `POST /process_patient_data` requires a patient JWT and enforces that the submitted `patient_id` matches the authenticated token.
- `POST /pull_cognitive_history`, `POST /upload_patient_images`, and `GET /patient_image_summaries` are caregiver-only routes.
- Image uploads are summarized with Ollama and only the text summaries are persisted.
- Removed endpoints are documented in [API_GUIDE.md](./API_GUIDE.md).
