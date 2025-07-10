import json
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nltk.tokenize import word_tokenize, sent_tokenize
import spacy
import benepar
import textstat
from sentence_transformers import SentenceTransformer
import re

from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

nlp = spacy.load('en_core_web_sm')
if not nlp.has_pipe('benepar'):
    nlp.add_pipe('benepar', config={'model': 'benepar_en3'})

sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

baseline = {}  # patient -> feature dict
history = {}   # patient -> list of daily records

def compute_features(transcript_text: str, duration_sec: float, segments: Optional[List[Dict[str, Any]]] = None, baseline_embedding: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Compute linguistic features from a transcript."""

    if segments is None:
        segments = []

    # --- basic tokenization ---
    try:
        words = word_tokenize(transcript_text.lower())
    except Exception:
        words = []
    try:
        sentences = sent_tokenize(transcript_text)
    except Exception:
        sentences = []

    total_words = len(words)
    num_sentences = len(sentences)
    unique_words = len(set(words))

    # Words spoken per second
    speech_speed = total_words / duration_sec if duration_sec > 0 else 0.0

    # --- pause statistics ---
    marker_pauses = len(re.findall(r"\.\.\.|<pause>", transcript_text))
    gap_durations = []
    for i in range(1, len(segments)):
        try:
            prev_end = float(segments[i - 1]["end"])
            start = float(segments[i]["start"])
            gap = start - prev_end
        except Exception:
            continue
        if gap > 0.3:
            gap_durations.append(gap)
    num_pauses = marker_pauses + len(gap_durations)
    pause_mean = float(np.mean(gap_durations)) if gap_durations else 0.0
    pause_var = float(np.var(gap_durations)) if gap_durations else 0.0

    # --- vocabulary statistics ---
    vocab_richness = unique_words / total_words if total_words > 0 else 0.0
    # filler_count = sum(1 for word in words if word in FILLER_WORDS)
    # filler_word_rate = filler_count / total_words if total_words > 0 else 0.0
    if total_words > 0:
        lexical_diversity = textstat.lexicon_count(transcript_text) / total_words
    else:
        lexical_diversity = 0.0
    avg_sentence_length = total_words / num_sentences if num_sentences > 0 else 0.0

    # --- syntactic features ---
    doc = nlp(transcript_text) if transcript_text.strip() else None
    #avg_parse_depth = get_avg_parse_depth(doc) if doc else 0.0
    dep_lengths = []
    if doc:
        for tok in doc:
            if tok.dep_ != "ROOT":
                dep_lengths.append(abs(tok.i - tok.head.i))
    avg_dependency_length = float(np.mean(dep_lengths)) if dep_lengths else 0.0

    # --- articulation ---
    syllable_count = textstat.syllable_count(transcript_text)
    speech_articulation_rate = syllable_count / duration_sec if duration_sec > 0 else 0.0

    # --- discourse coherence ---
    #coherence_score = compute_coherence_score(transcript_text)

    # --- repetition ---
    word_counts = Counter(words)
    repeated_words = 0
    for w, c in word_counts.items():
        if c > 1:
            repeated_words += 1
    repetition_rate = repeated_words / total_words if total_words > 0 else 0.0

    # --- pronoun vs noun usage ---
    pronoun_count = 0
    noun_count = 0
    if doc:
        for token in doc:
            if token.pos_ == "PRON":
                pronoun_count += 1
            elif token.pos_ == "NOUN":
                noun_count += 1
    pronoun_noun_ratio = pronoun_count / noun_count if noun_count > 0 else 0.0

    # --- verb tense ratios ---
    verbs = []
    if doc:
        for token in doc:
            if token.pos_ in {"VERB", "AUX"} or token.tag_ == "MD":
                verbs.append(token)
    verb_total = len(verbs)

    present_count = 0
    past_count = 0
    future_count = 0
    for token in verbs:
        if "Tense=Pres" in token.morph or token.tag_ in {"VBP", "VBZ", "VBG"}:
            present_count += 1
        if "Tense=Past" in token.morph or token.tag_ in {"VBD", "VBN"}:
            past_count += 1
        if token.tag_ == "MD" or "Tense=Fut" in token.morph:
            future_count += 1
    tense_ratio_present = present_count / verb_total if verb_total > 0 else 0.0
    tense_ratio_past = past_count / verb_total if verb_total > 0 else 0.0
    tense_ratio_future = future_count / verb_total if verb_total > 0 else 0.0

    # --- embedding similarity to baseline ---
    semantic_similarity_drift = 0.0
    if baseline_embedding is not None:
        try:
            emb = sentence_model.encode(transcript_text)
            dot = float(np.dot(emb, baseline_embedding))
            denom = np.linalg.norm(emb) * np.linalg.norm(baseline_embedding)
            similarity = dot / denom
            semantic_similarity_drift = 1.0 - similarity
        except Exception:
            semantic_similarity_drift = 0.0

    # --- assemble results ---
    features = {
        "speech_speed": float(speech_speed),  # words per second
        "pauses": float(num_pauses),  # total number of pauses
        "pause_mean": float(pause_mean),  # average pause duration
        "pause_var": float(pause_var),  # variance of pause durations
        "vocab_richness": float(vocab_richness),  # unique words / total words
        "filler_word_rate": float(filler_word_rate),  # proportion of filler words
        "lexical_diversity": float(lexical_diversity),  # lexical diversity score
        "avg_sentence_length": float(avg_sentence_length),  # words per sentence
        #"avg_parse_depth": float(avg_parse_depth),  # parse tree depth
        "speech_articulation_rate": float(speech_articulation_rate),  # syllables per second
        #"coherence_score": float(coherence_score),  # topic coherence variance
        "repetition_rate": float(repetition_rate),  # repeated word ratio
        "pronoun_noun_ratio": float(pronoun_noun_ratio),  # pronouns to nouns
        "avg_dependency_length": float(avg_dependency_length),  # dependency distance
        "tense_ratio_present": float(tense_ratio_present),  # share of present tense verbs
        "tense_ratio_past": float(tense_ratio_past),  # share of past tense verbs
        "tense_ratio_future": float(tense_ratio_future),  # share of future tense verbs
        "semantic_similarity_drift": float(semantic_similarity_drift),  # difference from baseline
    }

    return features

def load_whisper_outputs(json_path: str) -> List[Dict[str, Any]]:
    """Load Whisper transcript segments from a JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('segments', [])

def update_patient_day_from_json(patient_id: str, day: int, json_path: str, baseline_emb: Optional[np.ndarray] = None):
    segments = load_whisper_outputs(json_path)
    transcript = ' '.join(seg.get('text', '') for seg in segments)
    duration = segments[-1]['end'] if segments else 0
    features = compute_features(transcript, duration, segments, baseline_emb)
    if patient_id not in history:
        history[patient_id] = []
    history[patient_id].append({'day': day, **features})
    if patient_id not in baseline:
        baseline[patient_id] = features

    return features

def plot_trends(patient_id: str):
    df = pd.DataFrame(history.get(patient_id, []))
    if df.empty:
        print('No history for', patient_id)
        return
    df.set_index('day', inplace=True)
    df.plot(subplots=True, figsize=(12, 18), marker='o')
    plt.suptitle(f'Patient {patient_id} - Speech Feature Trends')
    plt.tight_layout()
    plt.show()

def generate_explainable_report(patient_id: str):
    if patient_id not in baseline or patient_id not in history:
        print('No data for', patient_id)
        return
    latest = history[patient_id][-1]
    base = baseline[patient_id]
    print(f'Patient {patient_id} - Day {latest["day"]}')
    for k, v in latest.items():
        if k == 'day':
            continue
        change = ((v - base[k]) / base[k] * 100) if base[k] else 0
        print(f'{k}: {v:.3f} (change {change:+.1f}%)')
    print()

def train_multi_task_model(df: pd.DataFrame):
    feature_cols = [c for c in df.columns if c not in ['MMSE', 'MoCA', 'CDR', 'day']]
    X = df[feature_cols]
    y = df[['MMSE', 'MoCA', 'CDR']]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    print(f'Model MSE: {mse:.2f}')
    return model

def bootstrap_confidence_interval(data: np.ndarray, iterations: int = 1000, alpha: float = 0.05):
    samples = []
    n = len(data)
    for _ in range(iterations):
        resample = np.random.choice(data, size=n, replace=True)
        samples.append(np.mean(resample))
    lower = np.percentile(samples, 100 * (alpha / 2))
    upper = np.percentile(samples, 100 * (1 - alpha / 2))
    return lower, upper

