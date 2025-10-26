import os
import tempfile
from typing import List
import speech_recognition as sr
from pydub import AudioSegment
from src.utils.ffmpeg_finder import ensure_ffmpeg
import subprocess
import platform

# On Windows, suppress flashing console windows spawned by pydub/ffmpeg by
# monkeypatching pydub.utils.Popen to inject no-window startup flags.
if os.name == 'nt':
    try:
        import pydub.utils as _pdutils  # type: ignore
        _orig_popen = getattr(_pdutils, 'Popen', None)

        if _orig_popen is not None:
            def _quiet_popen(*args, **kwargs):  # type: ignore
                try:
                    si = kwargs.get('startupinfo')
                    if si is None:
                        si = subprocess.STARTUPINFO()
                    try:
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        si.wShowWindow = 0
                    except Exception:
                        pass
                    kwargs['startupinfo'] = si
                    cf = kwargs.get('creationflags', 0)
                    try:
                        cf |= subprocess.CREATE_NO_WINDOW
                    except Exception:
                        pass
                    kwargs['creationflags'] = cf
                except Exception:
                    pass
                return _orig_popen(*args, **kwargs)

            _pdutils.Popen = _quiet_popen  # type: ignore
    except Exception:
        # If monkeypatch fails, proceed without blocking – worst case, a console flickers.
        pass

# Public list of supported input extensions so GUI filters stay in sync
SUPPORTED_EXTENSIONS: list[str] = [
    '.wav', '.mp3', '.flac', '.ogg', '.aac', '.wma', '.m4a',
    '.mp4', '.webm', '.avi', '.mov', '.3gp', '.opus'
]

def _resolve_ffmpeg_exe() -> str | None:  # backwards-compat wrapper
    ffmpeg, _ = ensure_ffmpeg(allow_download=True)
    return str(ffmpeg) if ffmpeg else None

def convert_audio_to_text(audio_file, text_file, language: str = 'pt-BR', progress=None):
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

    # Configure ffmpeg/ffprobe path robustly (single prompt for both)
    ffmpeg_p, ffprobe_p = ensure_ffmpeg(allow_download=True)
    ffmpeg_path = str(ffmpeg_p) if ffmpeg_p else None
    ffprobe_path = str(ffprobe_p) if ffprobe_p else None
    if ffmpeg_path:
        # pydub primarily uses 'converter'; some versions also read 'ffmpeg'
        AudioSegment.converter = ffmpeg_path
        try:
            AudioSegment.ffmpeg = ffmpeg_path  # type: ignore[attr-defined]
        except Exception:
            pass
    # Try to point pydub to ffprobe as well if available
    if ffprobe_path:
        try:
            AudioSegment.ffprobe = ffprobe_path  # type: ignore[attr-defined]
        except Exception:
            pass
    # If not found, let pydub try "ffmpeg" from PATH. We'll fail gracefully below if missing.

    # Supported audio formats by pydub (exported so GUI can match)
    audio_extension = os.path.splitext(audio_file)[1].lower()
    if audio_extension not in SUPPORTED_EXTENSIONS:
        return False, f"Audio format not supported: {audio_extension}"

    # Helper: normalize and convert to 16kHz mono 16-bit PCM WAV
    def _to_wav_16k_mono(src_path: str) -> str | None:
        try:
            seg = AudioSegment.from_file(src_path)
            # Normalize loudness to ~ -20 dBFS
            try:
                change = -20.0 - (seg.dBFS if seg.dBFS != float('-inf') else -30.0)
                seg = seg.apply_gain(change)
            except Exception:
                pass
            seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_wav_path = tmp_wav.name
            tmp_wav.close()
            seg.export(tmp_wav_path, format='wav')
            return tmp_wav_path
        except FileNotFoundError as e:
            return None
        except Exception:
            return None

    # Build a WAV we can feed reliably to SpeechRecognition
    wav_path = None
    try:
        if audio_extension == '.wav':
            # Still ensure correct rate/channels/bit depth
            wav_path = _to_wav_16k_mono(audio_file)
        else:
            wav_path = _to_wav_16k_mono(audio_file)
        if not wav_path:
            return False, "Failed to prepare audio for transcription (conversion to WAV failed)."
    except Exception as e:
        return False, f"Failed to convert audio to WAV: {e}"

    # Helper: transcribe a wav segment path
    def _transcribe_wav_segment(wav_seg_path: str) -> tuple[bool, str]:
        try:
            with sr.AudioFile(wav_seg_path) as source:
                audio_data = recognizer.record(source)
                # Use chosen language (BCP-47), e.g., 'pt-BR', 'en-US'
                text = recognizer.recognize_google(audio_data, language=language)
                return True, text
        except sr.UnknownValueError:
            return True, ""  # treat as empty segment rather than failing the whole job
        except sr.RequestError as e:
            return False, f"Request error: {e}"
        except Exception as e:
            return False, f"Unexpected error during segment transcription: {e}"

    # If the audio is long, split into ~10s chunks to avoid API Bad Request and improve progress smoothness
    try:
        full = AudioSegment.from_wav(wav_path)
        max_ms = 10000  # 10 seconds per chunk
        chunks: List[AudioSegment] = []
        if len(full) <= max_ms:
            chunks = [full]
        else:
            for start in range(0, len(full), max_ms):
                end = min(len(full), start + max_ms)
                chunks.append(full[start:end])

        collected: list[str] = []
        tmp_paths: list[str] = []
        try:
            total = max(1, len(chunks))
            # Initial progress
            if progress:
                try: progress(0)
                except Exception: pass
            for i, seg in enumerate(chunks):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".part{i}.wav")
                tmp_paths.append(tmp.name)
                tmp.close()
                seg.export(tmp.name, format='wav')
                ok, piece = _transcribe_wav_segment(tmp.name)
                if not ok:
                    # If one chunk fails with Bad Request, report with context
                    return False, piece
                if piece:
                    collected.append(piece)
                # Report chunk-based progress
                if progress:
                    try:
                        pct = min(99.0, ((i + 1) / total) * 100.0)
                        progress(pct)
                    except Exception:
                        pass
        finally:
            # cleanup temp chunk files
            for p in tmp_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass

        final_text = "\n".join(collected).strip()
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(final_text)
        # Snap to 100% at the very end
        if progress:
            try: progress(100)
            except Exception: pass
        return True, f"Transcription saved successfully at '{text_file}'!"
    except FileNotFoundError as e:
        # This can also surface if ffmpeg was needed and not found
        return False, (
            "Failed to open audio file. Check if the file exists and if FFmpeg is available.\n"
            f"Details: {e}"
        )
    except Exception as e:
        return False, f"Unexpected error during transcription: {e}"
    finally:
        # cleanup main tmp wav
        try:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception:
            pass