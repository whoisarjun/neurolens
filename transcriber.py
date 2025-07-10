# Whisper model (hackathon edition)
# If ur going to make changes to the way the whisper part
# of the pipeline works, PLEASE make sure you generate everything
# in the same format so the rest of the code doesn't break.

import whisper
import json
import os
from tqdm import tqdm

# Function to add pauses into transcript
def stitch_up_transcript(segments, pause_threshold=3):
    if not segments:
        return ""

    stitched = segments[0]['text'].strip()
    for i in range(len(segments) - 1):
        gap = segments[i+1]['start'] - segments[i]['end']
        if gap > pause_threshold:
            stitched += " ... "
        else:
            stitched += " "
        stitched += segments[i+1]['text'].strip()

    return stitched

# Format transcript from whisper and put into json format
def format_transcript(patient_id: str, day_num: int, result: {}, pause_threshold=3):
    segments = result.get('segments', [])

    transcript_text = stitch_up_transcript(segments, pause_threshold)
    duration = segments[-1]['end'] if segments else 0

    avg_segment_len = sum(len(segment['text'].split()) for segment in segments) / len(segments) if segments else 0
    coherence_score = round(min(1.0, avg_segment_len / 15), 3)

    return {
        'patient_id': patient_id,
        'day_num': day_num,
        'duration_sec': duration,
        'transcript_text': transcript_text,
        'segments': [
            {
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text']
            }
            for segment in segments
        ]
    }

# Whisper model to transcribe audio
def transcribe_with_progress(path, chunk_sec=30):
    model = whisper.load_model("tiny")

    audio = whisper.load_audio(path)
    audio = whisper.pad_or_trim(audio)

    sr = whisper.audio.SAMPLE_RATE
    total_samples = audio.shape[0]
    chunk_samples = chunk_sec * sr
    chunks = [audio[i:i+chunk_samples] for i in range(0, total_samples, chunk_samples)]

    segments = []
    for i, chunk in enumerate(tqdm(chunks, desc="Transcribing chunks")):
        mel = whisper.log_mel_spectrogram(chunk).to(model.device)
        result = whisper.decode(model, mel)
        segments.append({
            "start": i * chunk_sec,
            "end": min((i + 1) * chunk_sec, total_samples / sr),
            "text": result.text.strip()
        })

    return {"segments": segments}
def transcribe(path, show_progress=True):
    model = whisper.load_model('tiny')

    if show_progress:
        result = transcribe_with_progress(path)
    else:
        result = model.transcribe(path, word_timestamps=True, language='en')

    return result

# Dump formatted json into a file
def dump(patient_id, day_num, result, path):
    json_data = format_transcript(patient_id, day_num, result)
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)

# Quick function to transcribe a file into the nice format
def prep_transcription(patient_id, day_num, path, save_path=None):
    result = transcribe(path)
    if save_path is None:
        i = 0
        while True:
            candidate = f"output{'' if i == 0 else i}.json"
            if not os.path.exists(candidate):
                save_path = candidate
                break
            i += 1
    dump(patient_id, day_num, result, save_path)

# prep_transcription('P001', 8, 'test.wav')
