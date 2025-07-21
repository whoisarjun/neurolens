from TTS.api import TTS
from pydub import AudioSegment
import numpy as np

tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)

def read(text: str, fp: str):
    tts.tts_to_file(text=text, file_path=fp, speaker=tts.speakers[0])

def reformat(fp: str, frame_rate=8000):
    audio = AudioSegment.from_wav(fp)
    audio_8k = audio.set_frame_rate(frame_rate)
    audio_8k.export("output.wav", format="wav")

def add_noise(fp: str, frame_rate=8000, scale=0.0015):
    audio = AudioSegment.from_wav(fp)

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples /= np.max(np.abs(samples))
    noise = np.random.normal(0, scale, samples.shape)  # Adjust 0.02 for noise volume

    noisy_samples = samples + noise
    noisy_samples = np.clip(noisy_samples, -1.0, 1.0)
    noisy_int16 = (noisy_samples * 32767).astype(np.int16)
    noisy_audio = AudioSegment(
        noisy_int16.tobytes(),
        frame_rate=frame_rate,
        sample_width=2,  # 2 bytes for int16
        channels=audio.channels
    )

    noisy_audio.export(fp, format="wav")
