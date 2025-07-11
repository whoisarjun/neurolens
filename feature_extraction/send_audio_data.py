import feature_extractor as fe
import transcriber
import json
import requests

# TODO: do something so that transcript_text becomes a list of all answers (pmo)

def extract_features(file_paths: list[str], patient_id: str, save_path=None, model='tiny', verbose=True):
    all_transcriptions = []
    all_features = {}
    for i, fp in enumerate(file_paths):
        print(f'[FEAT_EXT] Began processing file {i+1}/{len(file_paths)}')
        transcription = transcriber.transcribe(fp, model=model)
        print(f'[FEAT_EXT] Finished transcribing file {i + 1}/{len(file_paths)}')
        data = transcriber.format_transcript(patient_id, transcription)
        all_transcriptions.append(data['transcript_text'])

        transcript, duration, segments = data['transcript_text'], data['duration_sec'], data['segments']

        features = fe.compute_features(transcript, duration, segments)
        for key, value in features.items():
            all_features.setdefault(key, []).append(value)

        print(f'[FEAT_EXT] Finished processing file {i + 1}/{len(file_paths)}')

    final_extraction = {
        'patient_id': patient_id,
        'transcript_text': all_transcriptions,
        'features': {
            key: sum(values) / len(values) if all(isinstance(v, (int, float)) for v in values) else values[0]
            for key, values in all_features.items()
        }
    }

    print(f'[FEAT_EXT] Saving data')

    if save_path is None:
        return final_extraction
    else:
        with open(save_path, 'w') as f:
            json.dump(all_features, f, indent=4)

        return None

def send_to_server(data):
    try:
        response = requests.post("http://localhost:6767/process_patient_data", json=data)
        print("Server response:", response.status_code, response.json())
    except Exception as e:
        print("Failed to send data to server:", e)

sample = extract_features([
    '../test.wav', '../test.wav', '../test.wav'
], 'P001')
send_to_server(sample)
