"""Image conversion view: owns every dialog; all business logic lives in
``services.image_service.ImageService`` (reached via ``ctx.image_service``).
"""
from __future__ import annotations

import os
import tkinter as tk
import warnings
from tkinter import filedialog, messagebox, ttk

from PIL import Image

from ..context import AppContext
from ..widgets.progress import run_with_progress_status
from ...services.job_runner import OperationCancelled
from ...utils.console_log import log_error
from ...utils.user_settings import get_setting, set_setting

# Allow very large images by disabling Pillow's decompression bomb limit and warning.
try:
    Image.MAX_IMAGE_PIXELS = None  # Remove safety cap (use with caution)
    warnings.simplefilter('ignore', Image.DecompressionBombWarning)
except Exception:
    pass


def convert_image_action(ctx: AppContext) -> None:
    try:
        _open_conversion_type_dialog(ctx)
        ctx.conversion_service.log_success("image_convert", None, None, username=ctx.current_user)
    except Exception as e:
        ctx.conversion_service.log_error("image_convert", None, str(e), username=ctx.current_user)
        log_error(f"Image conversion dialog failed: {e}")


def _open_conversion_type_dialog(ctx: AppContext) -> None:
    """Lets the user pick "convert format" vs. "combine into PDF"."""
    root = ctx.root
    choice_window = tk.Toplevel(root)
    choice_window.title("Choose Conversion Type")
    choice_window.geometry("300x150")
    choice_window.resizable(False, False)
    choice_window.grab_set()

    def select_format():
        choice_window.destroy()
        _convert_image_format(ctx)

    def select_pdf():
        choice_window.destroy()
        _convert_images_to_pdf(ctx)

    ttk.Label(choice_window, text="Select the conversion type:").pack(pady=10)
    ttk.Button(choice_window, text="Convert Image Format", command=select_format).pack(pady=5, padx=20, fill='x')
    ttk.Button(choice_window, text="Convert Images to PDF", command=select_pdf).pack(pady=5, padx=20, fill='x')


def _convert_image_format(ctx: AppContext) -> None:
    """Selects images, picks an output format, and converts them."""
    root = ctx.root
    service = ctx.image_service

    image_files = filedialog.askopenfilenames(
        title="Select images to convert",
        initialdir=(get_setting("last_dir_image") or ""),
        filetypes=[
            ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico;*.webp;*.tiff;*.tif;*.svg"),
            ("All Files", "*.*"),
        ]
    )
    if not image_files:
        return

    set_setting("last_dir_image", os.path.dirname(image_files[0]))

    format_window = tk.Toplevel(root)
    format_window.title("Select Output Format")
    format_window.geometry("320x290")
    format_window.resizable(False, False)
    format_window.grab_set()

    ttk.Label(format_window, text="Choose the output format:").pack(pady=10)

    selected_format = tk.StringVar(value="png")
    for fmt in ("png", "jpg", "jpeg", "bmp", "gif", "ico", "svg"):
        text = "SVG (vector)" if fmt == 'svg' else fmt.upper()
        ttk.Radiobutton(format_window, text=text, variable=selected_format, value=fmt).pack(anchor='w', padx=20)

    def confirm_format():
        output_format = selected_format.get()
        format_window.destroy()

        trace_opts = None
        if output_format == 'svg':
            if not service.vtracer_available():
                messagebox.showerror(
                    "SVG unavailable",
                    "SVG output needs the 'vtracer' package.\n\n"
                    "Install it with:  pip install vtracer"
                )
                return
            trace_opts = _ask_svg_options(ctx)
            if trace_opts is None:
                return

        out_dir = filedialog.askdirectory(
            title="Select output folder",
            initialdir=(get_setting("last_dir_image_out") or get_setting("last_dir_image") or "")
        )
        if not out_dir:
            return
        set_setting("last_dir_image_out", out_dir)

        if output_format == 'svg':
            _run_vectorization(ctx, image_files, out_dir, trace_opts)
        else:
            _run_conversion(ctx, image_files, out_dir, output_format)

    ttk.Button(format_window, text="Confirm", command=confirm_format).pack(pady=10)


def _convert_images_to_pdf(ctx: AppContext) -> None:
    """Selects images and combines them into a single PDF file."""
    root = ctx.root
    service = ctx.image_service

    image_files = filedialog.askopenfilenames(
        title="Select images to convert to PDF",
        initialdir=(get_setting("last_dir_image") or ""),
        filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"), ("All Files", "*.*")]
    )
    if not image_files:
        return

    pdf_name = (
        os.path.splitext(os.path.basename(image_files[0]))[0] + ".pdf"
        if len(image_files) == 1 else "merged_images.pdf"
    )

    set_setting("last_dir_image", os.path.dirname(image_files[0]))
    output_pdf_path = filedialog.asksaveasfilename(
        title="Save PDF as",
        defaultextension=".pdf",
        initialfile=pdf_name,
        initialdir=(get_setting("last_dir_image") or ""),
        filetypes=[("PDF File", "*.pdf")]
    )
    if not output_pdf_path:
        return

    def work(report, set_status, cancel_event):
        return service.images_to_pdf(list(image_files), output_pdf_path, cancel_event, report, set_status)

    try:
        run_with_progress_status(root, "Creating PDF", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "PDF creation was cancelled.")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Error during conversion: {e}")
        return

    messagebox.showinfo("Success", f"PDF created successfully!\nSaved at: {output_pdf_path}")


def _ask_svg_options(ctx: AppContext):
    """Asks how to trace, returning a TraceOptions or None if cancelled.

    Presets cover the three kinds of image people actually bring; the Advanced
    panel stays collapsed but exposes the same values for anyone who wants to
    tune a stubborn image.
    """
    service = ctx.image_service
    win = tk.Toplevel(ctx.root)
    win.title("Convert to SVG")
    win.resizable(False, False)
    win.grab_set()
    try:
        win.transient(ctx.root)
    except Exception:
        pass

    result = {'opts': None}

    ttk.Label(win, text="What kind of image is this?").pack(anchor='w', padx=16, pady=(14, 6))

    preset_var = tk.StringVar(value='logo')
    hints = {
        'logo': "Flat colours and sharp edges. Smallest, cleanest files.",
        'illustration': "Balanced: about half the file size of Detailed photo.",
        'photo': "Keeps the most detail. Slower, and much larger files.",
    }
    for key in ('logo', 'illustration', 'photo'):
        ttk.Radiobutton(
            win, text=service.PRESET_LABELS[key], variable=preset_var, value=key
        ).pack(anchor='w', padx=24)
        ttk.Label(win, text=hints[key], foreground="#666").pack(anchor='w', padx=46, pady=(0, 4))

    bw_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(win, text="Black and white", variable=bw_var).pack(anchor='w', padx=24, pady=(4, 0))

    # --- Advanced (collapsed by default) ---
    adv_shown = {'on': False}
    adv_frame = ttk.Frame(win)

    vars_ = {
        'snap': tk.BooleanVar(value=True),
        'colors': tk.IntVar(value=8),
        'filter_speckle': tk.IntVar(value=16),
        'color_precision': tk.IntVar(value=6),
        'layer_difference': tk.IntVar(value=48),
        'path_precision': tk.IntVar(value=3),
        'curve': tk.StringVar(value='spline'),
        'denoise': tk.IntVar(value=0),
    }

    def load_preset(*_):
        opts = service.preset_options(preset_var.get())
        vars_['snap'].set(bool(opts.colors))
        vars_['colors'].set(opts.colors or 8)
        vars_['filter_speckle'].set(opts.filter_speckle)
        vars_['color_precision'].set(opts.color_precision)
        vars_['layer_difference'].set(opts.layer_difference)
        vars_['path_precision'].set(opts.path_precision)
        vars_['curve'].set(opts.mode)
        vars_['denoise'].set(opts.denoise)

    preset_var.trace_add('write', load_preset)
    load_preset()

    ttk.Checkbutton(
        adv_frame,
        text="Snap similar colours together (removes fuzzy edges)",
        variable=vars_['snap'],
    ).grid(row=0, column=0, columnspan=2, sticky='w', pady=(4, 6))

    spins = [
        ("Colours to keep", 'colors', 2, 256),
        ("Discard specks smaller than", 'filter_speckle', 0, 128),
        ("Colour precision", 'color_precision', 1, 8),
        ("Layer difference", 'layer_difference', 0, 128),
        ("Coordinate precision", 'path_precision', 1, 8),
        ("Reduce JPEG artifacts (0 = off)", 'denoise', 0, 10),
    ]
    for row, (text, key, lo, hi) in enumerate(spins, start=1):
        ttk.Label(adv_frame, text=text).grid(row=row, column=0, sticky='w', pady=2)
        ttk.Spinbox(
            adv_frame, from_=lo, to=hi, textvariable=vars_[key], width=6
        ).grid(row=row, column=1, sticky='e', padx=(12, 0))

    ttk.Label(adv_frame, text="Curves").grid(row=len(spins) + 1, column=0, sticky='w', pady=(6, 2))
    curve_box = ttk.Frame(adv_frame)
    curve_box.grid(row=len(spins) + 1, column=1, sticky='e')
    ttk.Radiobutton(curve_box, text="Smooth", variable=vars_['curve'], value='spline').pack(side='left')
    ttk.Radiobutton(curve_box, text="Straight", variable=vars_['curve'], value='polygon').pack(side='left')

    adv_btn = ttk.Button(win, text="▸ Advanced")

    def toggle_adv():
        adv_shown['on'] = not adv_shown['on']
        if adv_shown['on']:
            adv_btn.config(text="▾ Advanced")
            adv_frame.pack(fill='x', padx=24, pady=(0, 4), before=button_row)
        else:
            adv_btn.config(text="▸ Advanced")
            adv_frame.pack_forget()

    adv_btn.config(command=toggle_adv)
    adv_btn.pack(anchor='w', padx=20, pady=(10, 0))

    button_row = ttk.Frame(win)
    button_row.pack(fill='x', padx=16, pady=12)

    def confirm():
        base = service.preset_options(preset_var.get())
        try:
            result['opts'] = service.make_trace_options(
                colors=(int(vars_['colors'].get()) if vars_['snap'].get() else None),
                hard_alpha=base.hard_alpha,
                colormode=('binary' if bw_var.get() else 'color'),
                hierarchical=base.hierarchical,
                mode=vars_['curve'].get(),
                filter_speckle=int(vars_['filter_speckle'].get()),
                color_precision=int(vars_['color_precision'].get()),
                layer_difference=int(vars_['layer_difference'].get()),
                corner_threshold=base.corner_threshold,
                length_threshold=base.length_threshold,
                max_iterations=base.max_iterations,
                splice_threshold=base.splice_threshold,
                path_precision=int(vars_['path_precision'].get()),
                denoise=int(vars_['denoise'].get()),
            )
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid settings", "Please check the advanced values.", parent=win)
            return
        win.destroy()

    ttk.Button(button_row, text="Cancel", command=win.destroy).pack(side='right')
    ttk.Button(button_row, text="Convert", command=confirm).pack(side='right', padx=(0, 8))

    win.bind('<Return>', lambda _e: confirm())
    ctx.root.wait_window(win)
    return result['opts']


def _run_vectorization(ctx: AppContext, image_files, out_dir: str, opts) -> None:
    """Traces each selected raster image into an SVG."""
    root = ctx.root
    service = ctx.image_service

    def confirm_overwrite(dst: str) -> bool:
        return messagebox.askyesno("Overwrite File", f"{dst} already exists.\nOverwrite?")

    jobs = service.plan_jobs(list(image_files), out_dir, "svg", confirm_overwrite)
    if not jobs:
        messagebox.showinfo("Nothing to do", "No images to convert.")
        return

    max_long_edge = None
    biggest = service.biggest_job(jobs)
    if biggest and service.is_large_image(biggest.src):
        width, height = service.image_size(biggest.src)
        limit = service.SUGGESTED_MAX_LONG_EDGE
        if messagebox.askyesno(
            "Large image",
            f"{os.path.basename(biggest.src)} is {width}×{height}, which is a lot "
            "of detail to trace.\n\n"
            "An SVG scales to any size on its own, so tracing it at "
            f"{limit} pixels will look the same while keeping the file much "
            "lighter and the wait much shorter.\n\n"
            "Trace at the smaller size?",
        ):
            max_long_edge = limit

    if biggest:
        estimate = service.estimate_svg_mb(biggest.src, opts, max_long_edge)
        if estimate >= service.HEAVY_SVG_MB:
            if not messagebox.askyesno(
                "Heads up",
                "This one is packed with detail, so the SVG should come out around "
                f"{estimate:.0f} MB — heavier than the original, and slower to "
                "open than it.\n\n"
                "SVG is at its best with flat artwork, logos and line art. For an "
                "image like this, staying with PNG or JPG usually serves you "
                "better.\n\n"
                "Convert to SVG anyway?",
            ):
                return

    def work(report, set_status, cancel_event):
        return service.vectorize_batch(jobs, opts, max_long_edge, cancel_event, report, set_status)

    try:
        outcome = run_with_progress_status(root, "Converting to SVG", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "SVG conversion was cancelled.")
        return
    except Exception as exc:
        messagebox.showerror("Error", f"Error during conversion: {exc}")
        return

    _report_batch_result(outcome, len(jobs))


def _run_conversion(ctx: AppContext, image_files, out_dir: str, output_format: str) -> None:
    """Converts each selected image into the chosen output format."""
    root = ctx.root
    service = ctx.image_service

    def confirm_overwrite(dst: str) -> bool:
        return messagebox.askyesno("Overwrite File", f"{dst} already exists.\nOverwrite?")

    jobs = service.plan_jobs(list(image_files), out_dir, output_format, confirm_overwrite)
    if not jobs:
        messagebox.showinfo("Nothing to do", "No images to convert.")
        return

    def work(report, set_status, cancel_event):
        return service.convert_batch(jobs, output_format, cancel_event, report, set_status)

    try:
        outcome = run_with_progress_status(root, f"Converting to {output_format.upper()}", work)
    except OperationCancelled:
        messagebox.showinfo("Cancelled", "Image conversion was cancelled.")
        return
    except Exception as exc:
        messagebox.showerror("Error", f"Error during conversion: {exc}")
        return

    _report_batch_result(outcome, len(jobs))


def _report_batch_result(outcome, total: int) -> None:
    converted = len(outcome.converted)
    if outcome.errors and converted == 0:
        messagebox.showerror("Error", "No images were converted.\n" + "\n".join(outcome.errors[:5]))
    elif outcome.errors:
        messagebox.showwarning(
            "Partial Success",
            f"Converted {converted}/{total} images. Some failed:\n" + "\n".join(outcome.errors[:5]),
        )
    else:
        messagebox.showinfo("Success", f"Converted {converted}/{total} images successfully!")


__all__ = ["convert_image_action"]
