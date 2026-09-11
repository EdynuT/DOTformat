"""Video conversion view: owns every dialog; all business logic lives in
``services.video_service.VideoService`` (reached via ``ctx.video_service``).
"""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..context import AppContext
from ..widgets.progress import run_with_progress_status
from ...services.job_runner import OperationCancelled
from ...utils.user_settings import get_setting, set_setting


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
            _single_video_conversion(ctx, format_var.get())
        else:
            batch_video_conversion(ctx, format_var.get())

    ttk.Button(conv_win, text="Confirm", command=confirm).pack(pady=10)


def _single_video_conversion(ctx: AppContext, output_format: str) -> None:
    video_file = filedialog.askopenfilename(
        title="Select the video file",
        initialdir=(get_setting("last_dir_video") or ""),
        filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv;*.flv"), ("All Files", "*.*")]
    )
    if not video_file:
        return
    set_setting("last_dir_video", os.path.dirname(video_file))

    base_name = os.path.splitext(os.path.basename(video_file))[0]
    default_output = f"{base_name}_converted.{output_format}"
    output_file = filedialog.asksaveasfilename(
        title="Save converted video as",
        defaultextension=f".{output_format}",
        initialfile=default_output,
        initialdir=(get_setting("last_dir_video_out") or get_setting("last_dir_video") or ""),
        filetypes=[("Video", f"*.{output_format}")]
    )
    if not output_file:
        return
    set_setting("last_dir_video_out", os.path.dirname(output_file))

    service = ctx.video_service
    video_name = os.path.basename(video_file)

    def work(report, set_status, cancel_event):
        set_status(f"Converting {video_name} to {output_format.upper()}…")
        return service.convert_single(video_file, output_file, output_format, cancel_event, on_progress=report)

    try:
        run_with_progress_status(ctx.root, "Converting Video", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "Video conversion was cancelled.")
        return
    except Exception as exc:
        messagebox.showerror("Error", f"Unexpected error: {exc}")
        return

    messagebox.showinfo("Success", "Video conversion completed successfully.")


def batch_video_conversion(ctx: AppContext, output_format: str) -> None:
    """Batch convert videos in a folder."""
    root = ctx.root
    service = ctx.video_service

    input_dir = filedialog.askdirectory(title="Select the folder with videos to convert", initialdir=(get_setting("last_dir_video") or ""))
    if not input_dir:
        return
    set_setting("last_dir_video", input_dir)
    output_dir = filedialog.askdirectory(title="Select the directory to save converted videos", initialdir=(get_setting("last_dir_video_out") or get_setting("last_dir_video") or ""))
    if not output_dir:
        return
    set_setting("last_dir_video_out", output_dir)

    jobs = service.list_batch_jobs(input_dir, output_dir, output_format)
    if not jobs:
        messagebox.showwarning("Warning", "No videos found in the folder.")
        return

    def work(report, set_status, cancel_event):
        return service.convert_batch(
            jobs, output_format, cancel_event,
            on_progress=report, on_status=set_status, username=ctx.current_user,
        )

    try:
        outcome = run_with_progress_status(root, "Batch video conversion", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "Batch video conversion was cancelled.")
        return
    except Exception as exc:
        messagebox.showerror("Error", f"Unexpected error: {exc}")
        return

    converted = len(outcome.converted)
    if outcome.errors and converted == 0:
        messagebox.showerror("Error", "No videos were converted.\n" + "\n".join(outcome.errors[:5]))
    elif outcome.errors:
        messagebox.showwarning(
            "Partial Success",
            f"Converted {converted}/{len(jobs)} videos. Some failed:\n" + "\n".join(outcome.errors[:5]),
        )
    else:
        messagebox.showinfo("Conversion Completed", f"Converted {converted}/{len(jobs)} videos successfully!")


__all__ = ["video_conversion_action", "batch_video_conversion"]
