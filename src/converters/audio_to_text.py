import os
import sys
import speech_recognition as sr
from pydub import AudioSegment

def convert_audio_to_text(audio_file, text_file):
    recognizer = sr.Recognizer()

    # Configure the path for ffmpeg
    if getattr(sys, 'frozen', False):
        ffmpeg_dir = os.path.join(sys._MEIPASS, 'ffmpeg')
    else:
        ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg')

    ffmpeg_path = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
    AudioSegment.converter = ffmpeg_path

    # List of formats supported by pydub
    supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.aac', '.wma', '.m4a', '.mp4', '.webm', '.avi', '.mov', '.3gp']

    # Check the file format and convert to WAV if necessary
    audio_extension = os.path.splitext(audio_file)[1].lower()
    if audio_extension not in supported_formats:
        raise ValueError(f"Audio format not supported: {audio_extension}")

    if audio_extension != '.wav':
        audio = AudioSegment.from_file(audio_file)
        audio_file = os.path.splitext(audio_file)[0] + '.wav'
        audio.export(audio_file, format='wav')

    # Recognize the audio
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language='en-US')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            return True, f"Transcription saved successfully at '{text_file}'!"
        except sr.UnknownValueError:
            return False, "Could not understand the audio."
        except sr.RequestError as e:
            return False, f"Error requesting speech recognition results; {e}"