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
def format_transcript(patient_id: str, result: {}, pause_threshold=3):
    segments = result.get('segments', [])

    transcript_text = stitch_up_transcript(segments, pause_threshold)
    duration = segments[-1]['end'] if segments else 0

    avg_segment_len = sum(len(segment['text'].split()) for segment in segments) / len(segments) if segments else 0

    return {
        'patient_id': patient_id,
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
def transcribe(path, model='tiny'):
    model = whisper.load_model(model)

    result = model.transcribe(path, word_timestamps=True, language='en')

    return result

# Dump formatted json into a file
def dump(patient_id, result, path):
    json_data = format_transcript(patient_id, result)
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)

# Quick function to transcribe a file into the nice format
def prep_transcription(patient_id, path, save_path=None):
    result = transcribe(path)
    if save_path is None:
        i = 0
        while True:
            candidate = f"output{'' if i == 0 else i}.json"
            if not os.path.exists(candidate):
                save_path = candidate
                break
            i += 1
    dump(patient_id, result, save_path)

# prep_transcription('P001', 8, 'test.wav')
