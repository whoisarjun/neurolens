import feature_extractor as fe
import transcriber
import json

def extract_features(file_path: str, patient_id: str, day_num: int, save_path=None):

    transcription = transcriber.transcribe(file_path)
    data = transcriber.format_transcript(patient_id, day_num, transcription)

    transcript, duration, segments = data['transcript_text'], data['duration_sec'], data['segments']

    features = fe.compute_features(transcript, duration, segments)
    data['features'] = features

    if save_path is None:
        return data
    else:
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4)

        return None

def send_to_server():
    # IN PROGRESS
    pass

# extract_features('../test.wav', 'P001', 67, '../output.json')
