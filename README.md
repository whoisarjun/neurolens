# Neurolens: Dementia Speech Trend Tracker & Cognitive Score Predictor

**"Daily AI conversations for personalized, explainable dementia care."**

Neurolens is a complete pipeline for **speech-based cognitive monitoring** of dementia patients. We analyze daily spoken responses during short AI-led conversations to extract detailed linguistic features that correlate with cognitive function, building a **personalized trend**, **AI-powered cognitive score prediction**, and **explainable reporting**.

Our system combines OpenAI-powered **natural language dialogue**, **automatic speech recognition (ASR)** via Whisper, and **multi-task regression**, to offer an **accessible, non-invasive tool** for clinicians and caregivers. 

Patients engage in a quick daily AI conversation—5 simple questions in their native language. Their responses are automatically analyzed to track signs of cognitive change, allowing for early intervention and more informed care.

---

# Project Pipeline

## 1. Daily AI Conversation Check-In ✅ (Updated Interaction Flow)
Instead of passively recording background speech, Neurolens now conducts a **daily AI-powered voice conversation** with each patient.

- The patient receives a **notification** at a preset time.
- When tapped, it launches a **friendly AI chat**, powered by OpenAI.
- The AI **asks 5 clinically meaningful questions** in the patient’s **native language**, simulating a natural conversation.
- The patient responds verbally; no typing or button pressing needed.
- Speech is captured, transcribed, and analyzed in real-time.

This ensures **consistent, high-quality, and context-rich speech data** while staying effortless and engaging for the user.

## 2. Speech-to-Text (ASR)
Audio responses are transcribed using **Whisper**. The `prep_transcription()` function outputs a **JSON file** containing the full transcript and segment timestamps.

## 3. Feature Extraction
The `compute_features()` function extracts rich **linguistic and acoustic features** from the transcript:

- Speech speed, articulation rate
- Pause statistics
- Vocabulary richness
- Sentence complexity (parse depth, dependency distance)
- Discourse coherence
- Repetition rate
- Pronoun-to-noun ratio
- Verb tense ratios
- Semantic similarity drift vs personal baseline

## 4. Baseline & History Tracking
The system stores:
- A **personal baseline** (Week 1 average) for each patient
- A **daily history** of linguistic features

## 5. Trend Visualization
`plot_trends()` generates **visual plots** of each feature over time to help caregivers spot declines or recoveries.

## 6. Explainable Reports
`generate_explainable_report()` creates a **simple textual summary** that compares recent speech to the personal baseline, highlighting **percentage changes** in each tracked feature.

## 7. Cognitive Score Prediction
A **multi-task Ridge regression model** is built to predict:
- MMSE (Mini-Mental State Exam)
- MoCA (Montreal Cognitive Assessment)
- CDR (Clinical Dementia Rating)

> **Current status:** Model is architected but untrained due to the lack of a suitable dementia speech dataset. Training is a future milestone.

## 8. Transfer Learning
With enough training data, the model can be fine-tuned to new patients and generalized across diverse populations through **transfer learning**.

---

# Inputs & Outputs

## Inputs:
- **Patient audio responses** from AI-led conversations
- **Whisper JSON files**
- (Future) **Labels**: MMSE, MoCA, CDR

## Outputs:
- Per-patient **feature history**
- **Explainable reports** showing changes
- (Pending training) **Cognitive score predictions**
- **Trend plots**

---

# How to Run

1. Use `prep_transcription()` to convert speech to JSON.
2. Use `update_patient_day_from_json()` to populate `history` and `baseline`.
3. (Optional) Train the model via `train_multi_task_model()` — pending dataset.
4. Use `plot_trends()` and `generate_explainable_report()` to visualize progress.

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
