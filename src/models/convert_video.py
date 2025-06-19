import threading
import ffmpeg
import time
import cv2
import os
import re
import sys
from tkinter import filedialog, messagebox, ttk, Toplevel, DoubleVar

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
        filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv;*.flv"), ("All Files", "*.*")]
    )
    if not video_file:
        messagebox.showwarning("Warning", "No file selected.")
        return

    # Suggest default output file name based on input file name and chosen format
    base_name = os.path.splitext(os.path.basename(video_file))[0]
    default_output = os.path.join(f"{base_name}_converted.{output_format}")
    output_file = filedialog.asksaveasfilename(
        title="Save converted video as",
        defaultextension=f".{output_format}",
        initialfile=default_output,
        filetypes=[("Video", f"*.{output_format}")]
    )
    if not output_file:
        messagebox.showwarning("Warning", "No save location specified.")
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

            # Prepare ffmpeg command with progress info
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', video_file,
                '-vcodec', vcodec,
                '-acodec', acodec,
                output_file
            ]

            # Start ffmpeg process
            ffmpeg_process[0] = proc = (
                ffmpeg
                .input(video_file)
                .output(output_file, vcodec=vcodec, acodec=acodec)
                .global_args('-y')
                .compile()
            )
            # Use subprocess directly to capture output
            import subprocess
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

            for line in process.stderr:
                # Parse ffmpeg output for progress
                match = time_pattern.search(line)
                if match:
                    hours, minutes, seconds, ms = map(int, match.groups())
                    current_time = hours * 3600 + minutes * 60 + seconds + ms / 100.0
                    percent = min((current_time / total_duration) * 100, 100)
                    progress_var.set(percent)
                    progress_win.update_idletasks()
            process.wait()

            if process.returncode == 0:
                progress_var.set(100)
                progress_win.update_idletasks()
                messagebox.showinfo("Success", "Video conversion completed successfully.")
            else:
                messagebox.showerror("Error", "Conversion failed or was cancelled.")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
        finally:
            progress_win.destroy()

    # Start conversion in a separate thread to keep UI responsive
    threading.Thread(target=run_conversion, daemon=True).start()