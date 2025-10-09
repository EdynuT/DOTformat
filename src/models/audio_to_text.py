import os
import sys
import speech_recognition as sr
from pydub import AudioSegment

def convert_audio_to_text(audio_file, text_file):
    """
    Converts an audio file to text using speech recognition.
    If the audio is not in WAV format, it is first converted using pydub.
    
    Parameters:
      - audio_file: Path to the input audio.
      - text_file: Path where the transcription will be saved.
      
    Returns:
      A tuple (True, success message) if successful, or (False, error message).
    """
    recognizer = sr.Recognizer()
    if not audio_file or not text_file:
        return False, "Missing input audio or output text path."

    # Configure ffmpeg path, adjusting if running in a bundled environment
    if getattr(sys, 'frozen', False):
        ffmpeg_dir = os.path.join(sys._MEIPASS, 'ffmpeg')
    else:
        ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg')
    ffmpeg_path = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
    AudioSegment.converter = ffmpeg_path

    # Supported audio formats by pydub
    supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.aac', '.wma', '.m4a', '.mp4', '.webm', '.avi', '.mov', '.3gp']
    audio_extension = os.path.splitext(audio_file)[1].lower()
    if audio_extension not in supported_formats:
        raise ValueError(f"Audio format not supported: {audio_extension}")

    # Convert to WAV if the audio is not already in WAV format
    if audio_extension != '.wav':
        audio = AudioSegment.from_file(audio_file)
        audio_file = os.path.splitext(audio_file)[0] + '.wav'
        audio.export(audio_file, format='wav')

    # Use the SpeechRecognition module to transcribe the audio
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language='en-US')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            return True, f"Transcription saved successfully at '{text_file}'!"
        except sr.UnknownValueError:
            return False, "Could not understand audio."
        except sr.RequestError as e:
            return False, f"Request error: {e}"