# API Guide

This guide covers the current API flow for the Flutter app, including authentication, patient session handling, caregiver access, and image uploads.

## Overview

- Patients log in and receive an `access_token` and `refresh_token`.
- The `access_token` is used for authenticated API calls.
- When the `access_token` expires, use the `refresh_token` to get a new token pair.
- If the `refresh_token` also expires, the user must log in again.

## Authentication Flow

1. Log in with `POST /auth/login`.
2. Store both `access_token` and `refresh_token`.
3. Use the `access_token` for authenticated requests.
4. Refresh tokens with `POST /auth/refresh` when needed.
5. If refresh fails because the token is expired, send the user back through login.

## Endpoints

### 1. `POST /auth/login`

Log in and obtain access and refresh tokens.

#### Request

```json
{
  "patient_id": "P001",
  "password": "password in plaintext",
  "role": "patient"
}
```

`role` can be either `"patient"` or `"caregiver"`.

#### Response

```json
{
  "access_token": "JWT string here",
  "refresh_token": "another JWT string here"
}
```

#### Notes

- Store both tokens securely.
- Use the `access_token` for normal authenticated requests.
- If the refresh token expires, the only recovery path is logging in again.

### 2. `POST /auth/refresh`

Get a new access token and refresh token using the current refresh token.

#### Request

Headers:

```http
Authorization: Bearer <refresh_token>
```

#### Response

```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token"
}
```

#### Notes

- Always replace the stored `access_token` and `refresh_token` with the new values.
- This keeps the user logged in as long as they continue using the app within the configured refresh window.
- The exact duration depends on the server `.env` configuration.

### 3. `POST /process_patient_data`

Submit one completed patient session.

Role: `patient` only

#### Request

Headers:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Body:

```json
{
  "patient_id": "P001",
  "transcript_text": [
    "answer 1",
    "answer 2",
    "answer 3",
    "answer 4",
    "answer 5"
  ],
  "features": [0.12, 4.8, 19, 0.003]
}
```

#### Rules

- `patient_id` must match the authenticated patient in the JWT.
- `transcript_text` must be a non-empty list of strings.
- `features` must be a non-empty list of numbers.

#### Response

```json
{
  "message": "Data appended for patient P001",
  "next_questions": [
    "new question 1",
    "new question 2",
    "new question 3",
    "new question 4",
    "new question 5"
  ]
}
```

#### Notes

- Stores the raw feature vector.
- Stores the current question and answer history.
- Generates the next 5 questions immediately.
- Returns those next questions in the same response.

### 4. `GET /next_questions`

Fetch the current pending questions for the authenticated patient.

Role: `patient` only

#### Request

Headers:

```http
Authorization: Bearer <access_token>
```

#### Response

```json
{
  "patient_id": "P001",
  "next_questions": [
    "question 1",
    "question 2",
    "question 3",
    "question 4",
    "question 5"
  ]
}
```

#### Notes

Use this when the app needs the latest saved questions without submitting a new completed session.

### 5. `POST /pull_cognitive_history`

Get a patient's stored cognitive history.

Role: `caregiver` only

#### Request

Headers:

```http
Authorization: Bearer <access_token>
```

Body:

```json
{
  "patient_id": "P001",
  "days": 50
}
```

#### Response

```json
{
  "cognitive_history": [
    {
      "date": "2026-04-14",
      "features": [0.12, 4.8, 19, 0.003]
    },
    {
      "date": "2026-04-13",
      "features": [0.11, 4.9, 18, 0.004]
    }
  ]
}
```

#### Notes

- If `days` is `-1`, the server returns the full history.
- Otherwise, the server returns entries from the past `days` days.

### 6. `POST /upload_patient_images`

Upload one or more patient images for processing.

Role: `caregiver` only

#### Request

Headers:

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Form data:

- Repeated field name: `image`

#### Behavior

- Each uploaded image is summarized with Ollama model `gemma4:e4b`.
- Each image is deleted from temporary storage immediately after processing.
- Only the text summary is stored in the database.
- The caregiver's JWT determines which patient the summaries belong to.

#### Response

```json
{
  "message": "Processed 2 images",
  "summaries": [
    {
      "id": 1,
      "patient_id": "P001",
      "date": "2026-04-14",
      "summary": "Dense factual summary of image 1..."
    },
    {
      "id": 2,
      "patient_id": "P001",
      "date": "2026-04-14",
      "summary": "Dense factual summary of image 2..."
    }
  ],
  "errors": []
}
```

#### Notes

- Partial success is supported.
- If some images fail, successful summaries are still stored and returned.
- Failed files may appear in the `errors` list.

### 7. `GET /patient_image_summaries`

Fetch stored image summaries for the authenticated caregiver's patient scope.

Role: `caregiver` only

#### Request

Headers:

```http
Authorization: Bearer <access_token>
```

#### Response

```json
{
  "patient_id": "P001",
  "image_summaries": [
    {
      "id": 2,
      "date": "2026-04-14",
      "summary": "Dense factual summary..."
    },
    {
      "id": 1,
      "date": "2026-04-14",
      "summary": "Another dense factual summary..."
    }
  ]
}
```

#### Notes

These summaries are also sampled at random, up to 5 per question-generation call, and included in prompt context for future question generation.

## Removed Endpoints

- `/upload_audio`
- `/generate_report`
