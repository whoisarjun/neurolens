import re
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from nltk.tokenize import word_tokenize, sent_tokenize
import spacy
import textstat
from sentence_transformers import SentenceTransformer

# Initialize Spacy & SentenceTransformer models once
nlp = spacy.load('en_core_web_sm')
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Define some filler words for filler_word_rate calculation
FILLER_WORDS = {"um", "uh", "like", "you know", "so", "actually", "basically", "right", "i mean"}

def compute_features(
    transcript_text: str,
    duration_sec: float,
    segments: Optional[List[Dict[str, Any]]] = None,
    baseline_embedding: Optional[np.ndarray] = None
) -> Dict[str, float]:

    if segments is None:
        segments = []

    # Tokenize words and sentences safely
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

    # Speech speed (words per second)
    speech_speed = total_words / duration_sec if duration_sec > 0 else 0.0

    # Pause statistics
    # Count pauses marked explicitly in transcript with ... or <pause>
    marker_pauses = len(re.findall(r"\.\.\.|<pause>", transcript_text))
    # Calculate gaps between Whisper segments > 0.3s as pauses
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

    # Vocabulary statistics
    vocab_richness = unique_words / total_words if total_words > 0 else 0.0

    # Filler word rate calculation
    filler_count = sum(1 for word in words if word in FILLER_WORDS)
    filler_word_rate = filler_count / total_words if total_words > 0 else 0.0

    # Lexical diversity using textstat lexicon count / total words
    lexical_diversity = textstat.lexicon_count(transcript_text) / total_words if total_words > 0 else 0.0

    # Average sentence length (words per sentence)
    avg_sentence_length = total_words / num_sentences if num_sentences > 0 else 0.0

    # Syntactic features - average dependency length
    doc = nlp(transcript_text) if transcript_text.strip() else None
    dep_lengths = []
    if doc:
        for tok in doc:
            if tok.dep_ != "ROOT":
                dep_lengths.append(abs(tok.i - tok.head.i))
    avg_dependency_length = float(np.mean(dep_lengths)) if dep_lengths else 0.0

    # Articulation rate - syllables per second
    syllable_count = textstat.syllable_count(transcript_text)
    speech_articulation_rate = syllable_count / duration_sec if duration_sec > 0 else 0.0

    # Repetition rate - ratio of words repeated more than once
    word_counts = Counter(words)
    repeated_words = sum(1 for w, c in word_counts.items() if c > 1)
    repetition_rate = repeated_words / total_words if total_words > 0 else 0.0

    # Pronoun to noun ratio
    pronoun_count = 0
    noun_count = 0
    if doc:
        for token in doc:
            if token.pos_ == "PRON":
                pronoun_count += 1
            elif token.pos_ == "NOUN":
                noun_count += 1
    pronoun_noun_ratio = pronoun_count / noun_count if noun_count > 0 else 0.0

    # Verb tense ratios (present, past, future)
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

    # Semantic similarity drift from baseline embedding
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

    # Assemble features dictionary
    features = {
        "speech_speed": float(speech_speed),  # words per second
        "pauses": float(num_pauses),  # total number of pauses
        "pause_mean": float(pause_mean),  # average pause duration
        "pause_var": float(pause_var),  # variance of pause durations
        "vocab_richness": float(vocab_richness),  # unique words / total words
        "filler_word_rate": float(filler_word_rate),  # proportion of filler words
        "lexical_diversity": float(lexical_diversity),  # lexical diversity score
        "avg_sentence_length": float(avg_sentence_length),  # words per sentence
        "speech_articulation_rate": float(speech_articulation_rate),  # syllables per second
        "repetition_rate": float(repetition_rate),  # repeated word ratio
        "pronoun_noun_ratio": float(pronoun_noun_ratio),  # pronouns to nouns
        "avg_dependency_length": float(avg_dependency_length),  # average dependency distance
        "tense_ratio_present": float(tense_ratio_present),  # present tense verbs ratio
        "tense_ratio_past": float(tense_ratio_past),  # past tense verbs ratio
        "tense_ratio_future": float(tense_ratio_future),  # future tense verbs ratio
        "semantic_similarity_drift": float(semantic_similarity_drift),  # 1 - similarity to baseline
    }

    return features
