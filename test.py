import audio_feature_extraction as afe
import transcriber
import json

file_path = 'test.wav'
save_path = 'output.json'
patient_id = 'P001'
day_num = 67

transcription = transcriber.transcribe(file_path)
data = transcriber.format_transcript(patient_id, day_num, transcription)

transcript, duration, segments = data['transcript_text'], data['duration_sec'], data['segments']

features = afe.compute_features(transcript, duration, segments)
data['features'] = features

with open(save_path, 'w') as f:
    json.dump(data, f, indent=4)
