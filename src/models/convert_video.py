import threading
import time
import cv2
import os
import re
import sys
import subprocess
from tkinter import filedialog, messagebox, ttk, Toplevel, DoubleVar
from src.utils.user_settings import get_setting, set_setting
from src.utils.ffmpeg_finder import ensure_ffmpeg
from src.services.conversion_service import ConversionService

def get_video_duration(video_file):
    """
    Returns the duration of the video in seconds using OpenCV.
    """
    cap = cv2.VideoCapture(video_file)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 1
    cap.release()
    return duration

def convert_video_choice(root, output_format):
    """
    Opens dialogs to select a video file and save location, then converts the video to the specified format.
    Shows a progress window with a progress bar and status message during conversion.
    Progress is updated in real time based on ffmpeg output.
    If the window is closed, the conversion is cancelled.
    """
    # Prompt user to select the input video file
    video_file = filedialog.askopenfilename(
        title="Select the video file",
        initialdir=(get_setting("last_dir_video") or ""),
        filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv;*.flv"), ("All Files", "*.*")]
    )
    if not video_file:
        # User cancelled the file dialog; do nothing.
        return

    # Suggest default output file name based on input file name and chosen format
    base_name = os.path.splitext(os.path.basename(video_file))[0]
    default_output = os.path.join(f"{base_name}_converted.{output_format}")
    if video_file:
        set_setting("last_dir_video", os.path.dirname(video_file))
    output_file = filedialog.asksaveasfilename(
        title="Save converted video as",
        defaultextension=f".{output_format}",
        initialfile=default_output,
        initialdir=(get_setting("last_dir_video_out") or get_setting("last_dir_video") or ""),
        filetypes=[("Video", f"*.{output_format}")]
    )
    if not output_file:
        # User cancelled the save dialog; do nothing.
        return

    # Get video duration in seconds for progress calculation
    total_duration = get_video_duration(video_file)

    # --- Progress Window Setup ---
    progress_win = Toplevel(root)
    progress_win.title("Converting Video")
    progress_win.geometry("400x120")
    progress_win.resizable(False, False)
    progress_win.grab_set()

    video_name = os.path.basename(video_file)
    lbl = ttk.Label(progress_win, text=f"Converting {video_name} to {output_format.upper()}...")
    lbl.pack(pady=10)

    progress_var = DoubleVar()
    progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100, length=350)
    progress_bar.pack(pady=10)

    # This variable will hold the ffmpeg process so we can terminate it if needed
    ffmpeg_process = [None]

    def on_close():
        # If the user closes the window, terminate the ffmpeg process if running
        if ffmpeg_process[0] is not None and ffmpeg_process[0].poll() is None:
            ffmpeg_process[0].terminate()
            messagebox.showinfo("Cancelled", "Video conversion cancelled.")
        progress_win.destroy()

    progress_win.protocol("WM_DELETE_WINDOW", on_close)

    def _ffmpeg_exe() -> str:
        ffmpeg, _ = ensure_ffmpeg(allow_download=True)
        if ffmpeg and os.path.exists(str(ffmpeg)):
            return str(ffmpeg)
        return 'ffmpeg'

    def run_conversion():
        try:
            # Build ffmpeg command
            if output_format.lower() == 'mp4':
                vcodec = 'libx264'
                acodec = 'aac'
            elif output_format.lower() == 'avi':
                vcodec = 'mpeg4'
                acodec = 'mp3'
            elif output_format.lower() == 'mov':
                vcodec = 'libx264'
                acodec = 'aac'
            else:
                vcodec = 'libx264'
                acodec = 'aac'

            # Prepare ffmpeg command with progress info (use bundled ffmpeg if available)
            cmd = [
                _ffmpeg_exe(),
                '-y',  # Overwrite output
                '-i', video_file,
                '-vcodec', vcodec,
                '-acodec', acodec,
                output_file
            ]

            # Start ffmpeg process using subprocess to capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            ffmpeg_process[0] = process

            # Regex to extract time= from ffmpeg output
            time_pattern = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')

            # Gentle nudge thread to avoid perceived freeze near the end
            stop_nudge = threading.Event()
            last_update = {'t': time.time()}

            def nudger():
                while not stop_nudge.is_set():
                    time.sleep(0.25)
                    # If no new update for 1.5s, nudge up to 99%
                    if (time.time() - last_update['t']) > 1.5:
                        cur = progress_var.get()
                        if cur < 99.0 and process.poll() is None:
                            progress_var.set(min(99.0, cur + 0.4))
                            try:
                                progress_win.update_idletasks()
                            except Exception:
                                pass
            threading.Thread(target=nudger, daemon=True).start()

            for line in process.stderr:
                # Parse ffmpeg output for progress
                match = time_pattern.search(line)
                if match:
                    h = int(match.group(1)); m = int(match.group(2)); s = int(match.group(3)); ms = float(match.group(4))
                    current_time = h * 3600 + m * 60 + s + (ms / 100.0)
                    # Cap parse-based progress at 98% to keep room for finalization
                    percent = min((current_time / max(1e-6, total_duration)) * 100, 98.0)
                    progress_var.set(percent)
                    last_update['t'] = time.time()
                    progress_win.update_idletasks()
            process.wait()

            # Stop nudger
            stop_nudge.set()

            if process.returncode == 0:
                progress_var.set(100)
                progress_win.update_idletasks()
                messagebox.showinfo("Success", "Video conversion completed successfully.")
                try:
                    ConversionService().log_success("video_convert", video_file, output_file)
                except Exception:
                    pass
            else:
                messagebox.showerror("Error", "Conversion failed or was cancelled.")
                try:
                    ConversionService().log_error("video_convert", video_file, "Conversion failed or cancelled")
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
            try:
                ConversionService().log_error("video_convert", video_file, str(e))
            except Exception:
                pass
        finally:
            progress_win.destroy()

    # Start conversion in a separate thread to keep UI responsive
    threading.Thread(target=run_conversion, daemon=True).start()

def convert_video_file(input_file: str, output_file: str, output_format: str) -> tuple[bool, str]:
    """Convert a single video file without UI. Returns (success, message).

    Uses ffmpeg via subprocess and blocks until completion.
    """
    try:
        # Choose codecs based on extension
        fmt = output_format.lower()
        if fmt == 'mp4':
            vcodec, acodec = 'libx264', 'aac'
        elif fmt == 'avi':
            vcodec, acodec = 'mpeg4', 'mp3'
        elif fmt == 'mov':
            vcodec, acodec = 'libx264', 'aac'
        else:
            vcodec, acodec = 'libx264', 'aac'

        # Resolve ffmpeg exe
        def _ffmpeg_exe() -> str:
            ffmpeg, _ = ensure_ffmpeg(allow_download=True)
            if ffmpeg and os.path.exists(str(ffmpeg)):
                return str(ffmpeg)
            return 'ffmpeg'

        cmd = [
            _ffmpeg_exe(), '-y',
            '-i', input_file,
            '-vcodec', vcodec,
            '-acodec', acodec,
            output_file
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        # Consume output to avoid blocking
        for _ in process.stderr:
            pass
        process.wait()
        if process.returncode == 0:
            return True, "Converted successfully."
        return False, "Conversion failed."
    except Exception as e:
        return False, f"Error: {e}"