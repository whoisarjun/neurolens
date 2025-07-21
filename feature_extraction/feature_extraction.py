# speech_analysis_suite.py
# Unified speech‑analysis toolkit — **v2: waveform‑only articulation rate**

# ── Imports ────────────────────────────────────────────────────────────────────
from __future__ import annotations
from typing import List, Tuple, Optional, Dict

import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks
from pydub.silence import detect_silence

import librosa
import textstat  # kept only for optional transcript‑based metrics

import parselmouth
from parselmouth.praat import call

import torch
from transformers import Wav2Vec2Processor, Wav2Vec2Model

import scipy.signal as signal  # new — peak finding for syllable nuclei

# ── Fluency & pause analysis ──────────────────────────────────────────────────

def _load_audio_pydub(path: str) -> AudioSegment:
    return AudioSegment.from_wav(path)


def detect_pauses(
    audio: AudioSegment,
    min_silence_len: int,
    silence_thresh: int,
) -> List[Tuple[float, float]]:
    raw = detect_silence(audio, min_silence_len, silence_thresh)
    return [(s / 1000.0, e / 1000.0) for s, e in raw]


def compute_metrics(pauses: List[Tuple[float, float]], total_dur: float) -> Dict[str, float]:
    pause_lens = np.array([e - s for s, e in pauses])
    total_sil = float(pause_lens.sum())
    total_spch = total_dur - total_sil
    n = len(pause_lens)
    mean_p = float(pause_lens.mean()) if n else 0.0
    var_p = float(pause_lens.var(ddof=0)) if n else 0.0
    rate = (n / (total_spch / 60.0)) if total_spch > 0 else 0.0
    return {
        "total_duration_s": total_dur,
        "total_speech_time_s": total_spch,
        "total_silence_time_s": total_sil,
        "num_pauses": n,
        "mean_pause_length_s": mean_p,
        "pause_length_variance_s2": var_p,
        "pause_rate_per_min_speech": rate,
    }


def auto_thresholds(
    audio: AudioSegment,
    frame_ms: int = 20,
    noise_quantile: float = 0.10,
    pause_quantile: float = 0.50,
) -> Tuple[int, int]:
    frames = make_chunks(audio, frame_ms)
    dbfs = np.array([c.dBFS for c in frames])
    sil_thresh = int(np.percentile(dbfs, noise_quantile * 100))

    raw = detect_silence(audio, frame_ms, sil_thresh)
    lens = np.array([e - s for s, e in raw])
    min_sil = int(np.percentile(lens, pause_quantile * 100)) if lens.size else frame_ms * 10
    return sil_thresh, min_sil


def calibrate_silence_threshold(
    silence_audio: AudioSegment,
    margin_db: float = 6.0,
    frame_ms: int = 20,
    quantile: float = 0.90,
) -> int:
    frames = make_chunks(silence_audio, frame_ms)
    dbfs = np.array([f.dBFS for f in frames])
    noise_floor = np.percentile(dbfs, quantile * 100)
    return int(noise_floor + margin_db)


def analyze_fluency(
    audio_path: str,
    silence_audio_path: Optional[str] = None,
    frame_ms: int = 20,
    noise_quantile: float = 0.10,
    pause_quantile: float = 0.50,
    margin_db: float = 6.0,
    quantile: float = 0.90,
    default_min_silence_len: int = 200,
) -> Dict[str, float]:
    audio = _load_audio_pydub(audio_path)

    if silence_audio_path:
        ref = _load_audio_pydub(silence_audio_path)
        sil_thresh = calibrate_silence_threshold(ref, margin_db, frame_ms, quantile)
        min_sil = default_min_silence_len
    else:
        sil_thresh, min_sil = auto_thresholds(audio, frame_ms, noise_quantile, pause_quantile)

    pauses = detect_pauses(audio, min_sil, sil_thresh)
    return compute_metrics(pauses, audio.duration_seconds)

# ── Prosody analysis ───────────────────────────────────────────────────────────

def _load_audio_librosa(path: str) -> Tuple[np.ndarray, int]:
    y, sr = librosa.load(path, sr=None, mono=True)
    return y, sr


def get_speech_time(audio_path: str, silence_audio_path: Optional[str]) -> float:
    return analyze_fluency(audio_path, silence_audio_path)["total_speech_time_s"]


# ——— NEW: energy‑based syllable nuclei detection ————————————————

def _count_syllable_nuclei(
    y: np.ndarray,
    sr: int,
    hop_len: int = 512,
    energy_threshold: float = 0.3,
    min_peak_distance_s: float = 0.10,
) -> int:
    """Return the number of syllable‑like energy bursts in *y*.

    Parameters
    ----------
    y : np.ndarray
        Mono audio samples.
    sr : int
        Sample rate.
    hop_len : int, optional
        Hop length for frame‑level RMS, by default 512.
    energy_threshold : float, optional
        Minimum normalised energy (0–1) for a frame to be considered a peak, by default 0.3.
    min_peak_distance_s : float, optional
        Minimum spacing between peaks in seconds, by default 0.10.
    """
    # Short‑time energy envelope
    rms = librosa.feature.rms(y=y, hop_length=hop_len)[0]
    if rms.max() == 0:
        return 0
    env = rms / rms.max()

    # Peak picking
    min_dist_frames = int(min_peak_distance_s * sr / hop_len)
    peaks, _ = signal.find_peaks(env, height=energy_threshold, distance=max(min_dist_frames, 1))
    return len(peaks)


def analyze_prosody(
    audio_path: str,
    transcript: Optional[str] = None,  # kept for optional speech‑rate computation
    silence_audio_path: Optional[str] = None,
    fmin_hz: float = librosa.note_to_hz("C2"),
    fmax_hz: float = librosa.note_to_hz("C7"),
    frame_len: int = 1024,
    hop_len: int = 512,
) -> Dict[str, float | None]:
    """Compute pitch, intensity and rate metrics.

    *Articulation rate* is now **waveform‑only**, derived from energy‑based syllable nuclei.
    A transcript is **no longer required** — if provided, *speech rate* (words/s) is also returned.
    """
    speech_time = get_speech_time(audio_path, silence_audio_path)

    y, sr = _load_audio_librosa(audio_path)

    # Pitch (f0)
    f0 = librosa.yin(
        y,
        fmin_hz,
        fmax_hz,
        sr=sr,
        frame_length=frame_len,
        win_length=frame_len,
        hop_length=hop_len,
    )
    f0 = f0[~np.isnan(f0)]

    # Intensity (RMS -> dB)
    rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop_len)[0]
    dB = 20 * np.log10(rms + 1e-6)

    # Articulation rate (syllables per second of *speech*)
    n_syllables = _count_syllable_nuclei(y, sr, hop_len)
    art_rate = n_syllables / speech_time if speech_time else 0.0

    # Optional speech‑rate (words/s) using transcript if supplied
    spk_rate = None
    if transcript:
        words = len(transcript.split())
        spk_rate = words / speech_time if speech_time else 0.0

    # Aggregate stats
    mean_f0 = float(f0.mean()) if f0.size else 0.0
    var_f0 = float(f0.var()) if f0.size else 0.0
    range_f0 = float(f0.max() - f0.min()) if f0.size else 0.0
    mean_int = float(dB.mean())
    var_int = float(dB.var())

    return {
        "mean_f0_hz": mean_f0,
        "f0_variance_hz2": var_f0,
        "f0_range_hz": range_f0,
        "mean_intensity_db": mean_int,
        "intensity_variance_db2": var_int,
        "articulation_rate_sps": art_rate,
        "speech_rate_wps": spk_rate,
    }

# ── Voice‑quality analysis ────────────────────────────────────────────────────

def _load_sound_parsel(path: str) -> parselmouth.Sound:
    return parselmouth.Sound(path)


def compute_jitter(sound: parselmouth.Sound, min_pitch: float = 75.0, max_pitch: float = 500.0) -> float:
    pp = call(sound, "To PointProcess (periodic, cc)", min_pitch, max_pitch)
    return float(call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100)


def compute_shimmer(sound: parselmouth.Sound, min_pitch: float = 75.0, max_pitch: float = 500.0) -> float:
    pp = call(sound, "To PointProcess (periodic, cc)", min_pitch, max_pitch)
    return float(call(pp, "Get shimmer (local, dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6))


def compute_hnr(
    sound: parselmouth.Sound,
    time_step: float = 0.01,
    min_pitch: float = 75.0,
    silence_threshold: float = 0.1,
) -> float:
    h = call(sound, "To Harmonicity (cc)", time_step, min_pitch, silence_threshold)
    return float(call(h, "Get mean", 0, 0))


def analyze_voice_quality(audio_path: str) -> Dict[str, float]:
    snd = _load_sound_parsel(audio_path)
    return {
        "jitter_local_perc": compute_jitter(snd),
        "shimmer_local_db": compute_shimmer(snd),
        "harmonic_to_noise_ratio_db": compute_hnr(snd),
    }

# ── Spectral summary analysis ─────────────────────────────────────────────────

def compute_mfcc(audio_path: str, n_mfcc: int = 13) -> Tuple[np.ndarray, np.ndarray]:
    y, sr = _load_audio_librosa(audio_path)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    return mfcc.mean(axis=1), mfcc.var(axis=1)


def compute_formant_stats(
    audio_path: str,
    time_step: float = 0.01,
    max_formant: float = 5500.0,
    win_len: float = 0.025,
) -> Dict[str, float]:
    snd = _load_sound_parsel(audio_path)
    fm = call(snd, "To Formant (burg)", time_step, max_formant, win_len, 1)
    times = np.arange(0, snd.duration, time_step)

    def _vals(method: str, idx: int) -> np.ndarray:
        v = [call(fm, method, idx, t) for t in times]
        return np.array([x for x in v if x > 0])

    f1, f2 = _vals("Get value at time", 1), _vals("Get value at time", 2)
    b1, b2 = _vals("Get bandwidth at time", 1), _vals("Get bandwidth at time", 2)

    stats: Dict[str, float] = {}
    for label, arr, bw in [("formant1", f1, b1), ("formant2", f2, b2)]:
        if arr.size:
            stats[f"{label}_mean_hz"] = float(arr.mean())
            stats[f"{label}_bandwidth_mean_hz"] = float(bw.mean())
            stats[f"{label}_shift_hz"] = float(arr.max() - arr.min())
        else:
            stats[f"{label}_mean_hz"] = stats[f"{label}_bandwidth_mean_hz"] = stats[f"{label}_shift_hz"] = 0.0
    return stats


def analyze_spectral(audio_path: str) -> Dict[str, list | float]:
    mfcc_mu, mfcc_var = compute_mfcc(audio_path, 13)
    return {
        "mfcc_means": mfcc_mu.tolist(),
        "mfcc_variances": mfcc_var.tolist(),
        **compute_formant_stats(audio_path),
    }

# ── SSL embedding & drift analysis ────────────────────────────────────────────

def _load_audio_ssl(path: str, sr: int = 16000) -> Tuple[np.ndarray, int]:
    return librosa.load(path, sr=sr, mono=True)


def chunk_audio(audio: np.ndarray, sr: int, win_s: float) -> List[np.ndarray]:
    win = int(sr * win_s)
    return [audio[i : i + win] for i in range(0, len(audio) - win + 1, win)]


def extract_embeddings(
    chunks: List[np.ndarray],
    processor: Wav2Vec2Processor,
    model: Wav2Vec2Model,
    device: str = "cpu",
) -> np.ndarray:
    model.to(device)
    vecs = []
    for c in chunks:
        inp = processor(
            c,
            sampling_rate=processor.feature_extractor.sampling_rate,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            hid = model(
                inp.input_values.to(device),
                attention_mask=inp.get("attention_mask", None).to(device) if "attention_mask" in inp else None,
            ).last_hidden_state
        vecs.append(hid.mean(dim=1).squeeze(0).cpu().numpy())
    return np.vstack(vecs)


def compute_centroid(emb: np.ndarray) -> np.ndarray:
    return emb.mean(axis=0)


def compute_drift(emb: np.ndarray, base_cent: np.ndarray) -> np.ndarray:
    return np.linalg.norm(emb - base_cent, axis=1)


def analyze_embeddings(
    audio_path: str,
    baseline_centroid: Optional[np.ndarray] = None,
    model_name: str = "facebook/wav2vec2-base-960h",
    window_s: float = 2.0,
    device: str = "cpu",
) -> Dict[str, np.ndarray]:
    """Extract Wav2Vec2 embeddings + optional drift vs. baseline."""
    audio, sr = _load_audio_ssl(audio_path)
    chunks = chunk_audio(audio, sr, window_s)
    if not chunks:
        raise ValueError("Audio shorter than one window — increase window_s or use longer audio.")

    processor = Wav2Vec2Processor.from_pretrained(model_name)
    model = Wav2Vec2Model.from_pretrained(model_name)
    emb = extract_embeddings(chunks, processor, model, device)
    centroid = compute_centroid(emb)

    out: Dict[str, np.ndarray] = {
        "chunk_embeddings": emb,
        "session_centroid": centroid,
    }
    if baseline_centroid is not None:
        out["drifts"] = compute_drift(emb, baseline_centroid)
    return out

# ── Main entry‑point ──────────────────────────────────────────────────────────

def main(
    audio_path: str,
    silence_audio_path: str,
    transcript: Optional[str] = None,
    baseline_centroid: Optional[np.ndarray] = None,
) -> Dict[str, Dict]:
    """Run **all** analyses on the same audio clip.

    Returns
    -------
    dict
        A nested dictionary with keys:
        - 'fluency'
        - 'prosody'
        - 'voice_quality'
        - 'spectral'
        - 'ssl_embeddings'  (drifts included if baseline provided)
    """
    return {
        "fluency": analyze_fluency(audio_path, silence_audio_path),
        "prosody": analyze_prosody(audio_path, transcript, silence_audio_path),
        "voice_quality": analyze_voice_quality(audio_path),
        "spectral": analyze_spectral(audio_path),
        "ssl_embeddings": analyze_embeddings(audio_path, baseline_centroid),
    }

# Example:
# results = main("speech.wav", "silence.wav", transcript=my_transcript)
# print(results)
