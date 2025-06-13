
# Neurolens: Dementia Speech Trend Tracker & Cognitive Score Predictor

**"Passive speech monitoring for personalized, explainable Dementia care."**

Through this project, we built a complete pipeline for **speech-based cognitive monitoring** for dementia patients or patients suffering from memory loss. By analyzing daily speech recordings, the program extracts detailed linguistic features that correlate with cognitive function, creating a **personalized trend**, **AI-powered cognitive score prediction**, and **explainable reporting**.

Our approach leverages state-of-the-art **automatic speech recognition (ASR)** (Whisper) built by OpENai, **natural language processing (NLP)**, and **multi-task regression** to provide an **accessible, non-invasive, and fully passive tool** for clinicians and caregivers. The system monitors each patient's speech over time, spotting subtle changes and patterns and turning that into clear, understandable insights that a caregiver or medical professional can use for early intervention or more educated dementia care.

We originally intended to demonstrate **transfer learning** by training our cognitive score prediction model on the **MultiConAD** dataset. However, after further investigation, we discovered that **MultiConAD is not openly available**, and that there is currently a significant lack of publicly accessible, clinically labeled dementia speech datasets. Due to this data scarcity and the limited time available during the hackathon, our regression model is not yet trained; building an appropriate dataset will be an essential future step to enable this capability.

> **Note:**
> The regression model architecture is implemented, but remains untrained due to lack of appropriate data. Dataset collection and model training and accuracy will be prioritized in the next phase of the project.

---

# Project Pipeline

## 1. Daily Speech Collection
Patients' **natural speech** is passively recorded throughout the day, such as during conversations, phone calls, or interactions with others, requiring no active effort from the patient.

## 2. Speech-to-Text (ASR)
Audio is transcribed using **Whisper**. The `prep_transcription()` function produces an output that is a **JSON file** containing full transcript text and segment timestamps.

## 3. Feature Extraction
The `compute_features()` function extracts a wide range of **linguistic and acoustic features**:

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

- A **personal baseline** (Week 1 average) for each patient.
- A **history** of daily feature values per patient.

## 5. Trend Visualization
`plot_trends()` generates **visual plots** of each feature over time.

## 6. Explainable Reports
`generate_explainable_report()` outputs a **textual summary** comparing the latest speech to personal baseline, showing **% changes** in each feature.

## 7. Cognitive Score Prediction
A **multi-task Ridge regression model** is designed to predict:

- MMSE (Mini-Mental State Exam)
- MoCA (Montreal Cognitive Assessment)
- CDR (Clinical Dementia Rating)

> **Current status:**
> The model architecture is implemented, but remains untrained due to lack of publicly available dementia speech datasets. Future data collection will enable this critical component.

## 8. Transfer Learning
Once sufficient training data is available, the model will be trained and validated — enabling **transfer learning** and **generalization** to real patient data.

## Inputs

- **Whisper JSON files**: one per patient per day
- **Labels** (optional for training): MMSE, MoCA, CDR (future dataset required)

## Outputs

- Per-patient **feature history** (`history`)
- Per-patient **explainable reports**
- **Cognitive score predictions** (pending dataset availability)
- **Trend plots**

## How to Run

1️⃣ Use `prep_transcription()` to obtain JSON files.

2️⃣ Use `update_patient_day_from_json()` to populate `history` and `baseline`

3️⃣ (Optional) Load labels and run `train_multi_task_model()` → training pending dataset

4️⃣ Use `plot_trends()` and `generate_explainable_report()` to visualize and explain results  

# Planned Next Steps

While the current pipeline demonstrates a working system for **speech feature extraction**, **personalized trend tracking**, and **explainable reporting**, several key enhancements are planned to take this project further:

## 1. Build and Train Cognitive Score Predictor
- Due to the scarcity of public dementia speech datasets and the unavailability of MultiConAD, we have not yet been able to train a clinically validated cognitive score model.
- Priority next step:
    - Collaborate with clinicians and research partners to collect **real-world, annotated speech data** linked to cognitive scores.
    - Build a high-quality dataset suitable for training and validating our model.
    - Once data is available, train and validate the **multi-task regression model** to predict MMSE, MoCA, and CDR scores.
    - Apply the trained model to personal patient data.

## 2. Build Full App Interface
- The system will be integrated into a **non-invasive, passive monitoring app** for caregivers and clinicians.
- The app will capture **natural background speech** during daily life, requiring no active participation from the patient.
- Planned app features:
    - Automated background speech capture and processing
    - Real-time trend visualization dashboards
    - Simple, clear explainable reports for caregivers
    - Alerts when speech patterns suggest possible cognitive decline
    - Support for **personalized tracking** (baseline per patient) rather than fixed population thresholds

## 3. Optimize for Local & Secure Deployment
- **Quantize Whisper models** (e.g. using whisper.cpp or ONNX) to enable **efficient, local speech transcription** on-device, hence reducing compute cost and latency.
- Ensure that **all speech processing can be performed locally**, where required, to preserve patient privacy and minimize sensitive data transfer.
- Architect the system to support both **fully local mode** and **secure cloud mode** (where local is not feasible).

## 4. Expand Feature Set
- Explore additional **speech biomarkers** from recent dementia research.
- Incorporate **prosodic features** (intonation, rhythm, emotional tone).
- Investigate **multi-lingual support**, enabling application to diverse patient populations.

## 5. Robustness & Real-world Deployment
- Test pipeline on **real patient data** collected through collaboration with healthcare partners.
- Optimize pipeline for **lightweight, on-device** or **secure cloud** deployment to support practical clinical use.

## 6. Privacy & Security
- Implement **secure, privacy-preserving processing** of patient speech data.
- Ensure compliance with relevant **healthcare data standards** (e.g. HIPAA, GDPR).
- Support **local-first architecture** where sensitive data never leaves the device, when required.

---

## Long-term Vision

Our goal is to build a clinically meaningful **speech-based cognitive monitoring tool** that is:

- **Non-invasive & passive** → captures natural background speech, requires no patient effort  
- **Personalized** → tracks changes relative to each individual’s own baseline  
- **Explainable** → provides clear, trusted insights into what is changing and why  
- **Secure & local-first** → designed to run Whisper and the full pipeline locally where possible  
- **Accessible** → simple to use for caregivers and scalable across care settings  

By providing **continuous, transparent monitoring** of speech-based cognitive signals, this system aims to **empower earlier detection** of cognitive decline and enable **more personalized, proactive dementia care**.

# Acknowledgments

We would like to acknowledge:

- The developers of **Whisper** and **spaCy**, whose open models enable powerful speech and language processing.
- The open-source community for providing many of the tools used in this pipeline.
- Our team members and mentors for their contributions and guidance throughout the project.
- The organizers and judges of this hackathon for the opportunity to present and further develop this work.

