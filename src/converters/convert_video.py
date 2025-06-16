import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import ffmpeg

def convert_video(video_file, output_file, output_format):
    try:
        stream = ffmpeg.input(video_file)
        # Define basic codecs based on the chosen format
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
            # If the format is not recognized, use default (mp4)
            vcodec = 'libx264'
            acodec = 'aac'
        stream = ffmpeg.output(stream, output_file, vcodec=vcodec, acodec=acodec)
        ffmpeg.run(stream, overwrite_output=True)
        return True, "Conversion completed successfully."
    except Exception as e:
        return False, f"Conversion error: {str(e)}"

def convert_video_choice(root):
    # Allow the user to select the video file to convert
    video_file = filedialog.askopenfilename(
        title="Select the video file",
        filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv;*.flv"), ("All files", "*.*")]
    )
    if not video_file:
        messagebox.showwarning("Warning", "No file selected.")
        return

    # Create a new window for output format selection
    format_window = tk.Toplevel(root)
    format_window.title("Select Output Format")
    format_window.geometry("300x200")
    format_window.resizable(False, False)
    format_window.grab_set()

    label = ttk.Label(format_window, text="Choose the output format:")
    label.pack(pady=10)

    formats = ['mp4', 'avi', 'mov']
    selected_format = tk.StringVar(value=formats[0])
    for fmt in formats:
        rb = ttk.Radiobutton(format_window, text=fmt.upper(), variable=selected_format, value=fmt)
        rb.pack(anchor='w', padx=20)

    def confirm_format():
        format_window.destroy()
        # Suggest default name based on input file and output format
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        default_output = os.path.join(os.path.dirname(video_file), f"{base_name}_converted.{selected_format.get()}")
        output_file = filedialog.asksaveasfilename(
            title="Save converted video as",
            defaultextension=f".{selected_format.get()}",
            initialfile=default_output,
            filetypes=[("Video", f"*.{selected_format.get()}")]
        )
        if not output_file:
            messagebox.showwarning("Warning", "No save location specified.")
            return

        success, message = convert_video(video_file, output_file, selected_format.get())
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    btn_confirm = ttk.Button(format_window, text="Confirm", command=confirm_format)
    btn_confirm.pack(pady=10)