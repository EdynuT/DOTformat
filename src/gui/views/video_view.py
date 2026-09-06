"""Video conversion view: single-file (via convert_video_choice) or batch conversion."""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..context import AppContext
from ..widgets.progress import run_steps
from ...models.convert_video import convert_video_choice, convert_video_file
from ...utils.user_settings import get_setting, set_setting

VIDEO_EXTENSIONS = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')


def batch_video_conversion(ctx: AppContext, output_format: str) -> None:
    """Batch convert videos in a folder."""
    root = ctx.root
    conversion_service = ctx.conversion_service

    input_dir = filedialog.askdirectory(title="Select the folder with videos to convert", initialdir=(get_setting("last_dir_video") or ""))
    if not input_dir:
        return
    set_setting("last_dir_video", input_dir)
    output_dir = filedialog.askdirectory(title="Select the directory to save converted videos", initialdir=(get_setting("last_dir_video_out") or get_setting("last_dir_video") or ""))
    if not output_dir:
        return
    set_setting("last_dir_video_out", output_dir)
    videos = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(VIDEO_EXTENSIONS)]
    if not videos:
        messagebox.showwarning("Warning", "No videos found in the folder.")
        return

    def _do_batch(step):
        results = []
        for video_file in videos:
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
            try:
                ok, msg = convert_video_file(video_file, output_file, output_format)
                if ok:
                    conversion_service.log_success("video_batch", video_file, output_file, username=ctx.current_user)
                    results.append(f"{os.path.basename(video_file)}: Success")
                else:
                    conversion_service.log_error("video_batch", video_file, msg, username=ctx.current_user)
                    results.append(f"{os.path.basename(video_file)}: Error")
            except Exception as e:
                conversion_service.log_error("video_batch", video_file, str(e), username=ctx.current_user)
                results.append(f"{os.path.basename(video_file)}: Exception")
            finally:
                step(1)
        return "\n".join(results)

    summary = run_steps(root, "Batch video conversion", len(videos), _do_batch)
    messagebox.showinfo("Conversion Completed", summary)


def video_conversion_action(ctx: AppContext) -> None:
    """Lets the user choose between single video conversion or batch conversion."""
    root = ctx.root
    conv_win = tk.Toplevel(root)
    conv_win.title("Select Video Conversion Type")
    conv_win.geometry("300x300")
    conv_win.resizable(False, False)
    conv_win.grab_set()

    ttk.Label(conv_win, text="Choose conversion type:").pack(pady=10)

    conv_type = tk.StringVar(value="single")
    ttk.Radiobutton(conv_win, text="Single Video Conversion", variable=conv_type, value="single").pack(anchor="w", padx=20)
    ttk.Radiobutton(conv_win, text="Batch Video Conversion", variable=conv_type, value="batch").pack(anchor="w", padx=20)

    format_var = tk.StringVar(value="mp4")
    ttk.Label(conv_win, text="Select output format for batch conversion:").pack(pady=10)
    ttk.Radiobutton(conv_win, text="MP4", variable=format_var, value="mp4").pack(anchor="w", padx=40)
    ttk.Radiobutton(conv_win, text="AVI", variable=format_var, value="avi").pack(anchor="w", padx=40)
    ttk.Radiobutton(conv_win, text="MOV", variable=format_var, value="mov").pack(anchor="w", padx=40)

    def confirm():
        conv_win.destroy()
        if conv_type.get() == "single":
            convert_video_choice(root, format_var.get())
        else:
            batch_video_conversion(ctx, format_var.get())

    ttk.Button(conv_win, text="Confirm", command=confirm).pack(pady=10)


__all__ = ["video_conversion_action", "batch_video_conversion"]
