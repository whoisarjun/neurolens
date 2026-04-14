# Neurolens Backend

Neurolens is a lightweight backend for a daily patient conversation flow. The backend stores opaque feature vectors and question/answer history, generates the next set of questions for each patient, and serves that data back to clients.

The backend does not interpret feature indices, perform feature extraction, accept audio uploads, or generate explainability reports. Those concerns now live outside the backend.

---

# Project Pipeline

## 1. Daily Question Flow
- Each patient has a stored set of pending questions.
- The client fetches those questions and collects 5 answers.
- The client computes a numeric feature vector outside the backend.

## 2. Session Submission
- The client submits:
  - `patient_id`
  - `transcript_text` as the answer list
  - `features` as an opaque numeric vector
- The backend stores the feature vector unchanged.
- The backend stores the current question/answer pairs in history.

## 3. Next Question Generation
- After a successful submission, the backend generates the next question set.
- The new questions are persisted and returned to the client.

## 4. History Retrieval
- Caregivers can pull stored cognitive history.
- Patients can fetch their current pending questions.

---

# Inputs & Outputs

## Inputs:
- `transcript_text`: list of patient answers
- `features`: opaque numeric vector generated outside the backend

## Outputs:
- Per-patient stored feature-vector history
- Per-patient question/answer history
- Next generated questions for the next session

## Backend Database

This backend now uses a local SQLite database file instead of Supabase/Postgres.

- Default DB file: `neurolens.db` in the project root
- Optional override: set `SQLITE_DB_PATH` in `.env`
- Tables are created automatically on startup

---

# How to Run

1. Use `prep_transcription()` to convert speech to JSON.
2. Start the Flask server.
3. Use `POST /process_patient_data` to submit session results.
4. Use `GET /next_questions` to fetch the next pending questions.

---

# Planned Next Steps

## 1. Build and Train Cognitive Score Predictor
- Partner with clinicians to collect **real-world speech + cognitive scores**
- Train and validate multi-task regression model
- Predict MMSE, MoCA, and CDR based on linguistic data

## 2. Expand App Interface
- Embed AI conversation system into an **easy-to-use app**
- Features:
  - Daily speech capture via voice chat
  - Real-time trend dashboards
  - Simple explainable summaries
  - Caregiver alerts for cognitive decline
  - Personalized tracking (relative to personal baseline)

## 3. Local & Secure Deployment
- Use **quantized Whisper (e.g. whisper.cpp or ONNX)** for local ASR
- Support **on-device processing** to preserve privacy
- Allow both **local-first** and **secure cloud** deployment modes

## 4. Broaden Feature Set
- Add **prosodic features** (tone, rhythm)
- Enable **multilingual support** for global use

## 5. Real-World Testing
- Partner with clinics to trial in real conditions
- Optimize system for **on-device or hybrid deployment**

## 6. Privacy & Security
- Ensure compliance with **HIPAA**, **GDPR**
- Support **secure, privacy-first architecture**
- No data leaves the device without consent (local-first by default)

---

# Long-Term Vision

We aim to build the world's most **accessible, explainable, and proactive dementia monitoring tool**:

- 🧠 **Personalized** — tracks speech vs personal baseline  
- 🫥 **Passive-feeling** — requires only simple daily conversation  
- 🔍 **Explainable** — gives clear insight to caregivers  
- 🔐 **Private** — designed for local processing  
- 📱 **Accessible** — deployable in clinics, homes, anywhere  

By continuously and naturally tracking the cognitive health of patients, Neurolens empowers **earlier detection**, **personalized care**, and **better lives**.

---

# Acknowledgments

Huge thanks to:
- OpenAI (Whisper, GPT)
- spaCy + NLP open-source community
- Mentors & team members
- Hackathon organizers & judges
