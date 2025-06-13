import os
import sys
import speech_recognition as sr
from pydub import AudioSegment

def convert_audio_to_text(audio_file, text_file):
    recognizer = sr.Recognizer()

    # Configurando o caminho para o ffmpeg
    if getattr(sys, 'frozen', False):
        ffmpeg_dir = os.path.join(sys._MEIPASS, 'ffmpeg')
    else:
        ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg')

    ffmpeg_path = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
    AudioSegment.converter = ffmpeg_path

    # Lista de formatos suportados pelo pydub
    supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.aac', '.wma', '.m4a', '.mp4', '.webm', '.avi', '.mov', '.3gp']

    # Verificar o formato do arquivo e converter para WAV se necessário
    audio_extension = os.path.splitext(audio_file)[1].lower()
    if audio_extension not in supported_formats:
        raise ValueError(f"Formato de áudio não suportado: {audio_extension}")

    if audio_extension != '.wav':
        audio = AudioSegment.from_file(audio_file)
        audio_file = os.path.splitext(audio_file)[0] + '.wav'
        audio.export(audio_file, format='wav')

    # Reconhecer o áudio
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language='pt-BR')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            return True, f"Transcrição salva em '{text_file}' com sucesso!"
        except sr.UnknownValueError:
            return False, "Não foi possível entender o áudio."
        except sr.RequestError as e:
            return False, f"Erro ao solicitar resultados do serviço de reconhecimento de fala; {e}"