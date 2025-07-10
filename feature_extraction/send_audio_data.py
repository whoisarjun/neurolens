import feature_extractor as fe
import transcriber
import json
import requests

# TODO: do something so that transcript_text becomes a list of all answers (pmo)

def extract_features(file_path: str, patient_id: str, save_path=None):

    transcription = transcriber.transcribe(file_path)
    data = transcriber.format_transcript(patient_id, 0, transcription)

    transcript, duration, segments = data['transcript_text'], data['duration_sec'], data['segments']

    features = fe.compute_features(transcript, duration, segments)
    data['features'] = features

    if save_path is None:
        return data
    else:
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4)

        return None

def send_to_server(data):
    del sample_data['segments']
    try:
        response = requests.post("http://localhost:6767/process_patient_data", json=data)
        print("Server response:", response.status_code, response.json())
    except Exception as e:
        print("Failed to send data to server:", e)

sample_data = extract_features('../test.wav', 'P001')
send_to_server(sample_data)
